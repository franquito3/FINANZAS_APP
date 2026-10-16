import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import '../config/app_config.dart';
import '../models/transaction_model.dart';
import 'local_storage_service.dart';

class SyncResult {
  final bool success;
  final int syncedCount;
  final String message;

  const SyncResult({
    required this.success,
    required this.syncedCount,
    required this.message,
  });
}

class SupabaseSyncService {
  final LocalStorageService _localStorage;
  bool _isSyncing = false;

  SupabaseSyncService(this._localStorage);

  SupabaseClient get _client => Supabase.instance.client;

  User? get currentUser => _client.auth.currentUser;
  String? get userId => currentUser?.id;
  String? get userEmail => currentUser?.email;
  bool get isLoggedIn => currentUser != null;

  Stream<AuthState> get authStateChanges => _client.auth.onAuthStateChange;

  /// Inicio de sesión con Correo y Contraseña directo en la app (sin navegador externo)
  Future<(bool, String)> signInWithEmail(String email, String password) async {
    try {
      final res = await _client.auth.signInWithPassword(
        email: email.trim(),
        password: password,
      );
      if (res.user != null) {
        return (true, '¡Bienvenido, ${res.user!.email ?? ''}! ');
      }
      return (false, 'No se pudo iniciar sesión.');
    } on AuthException catch (e) {
      return (false, _translateAuthError(e.message));
    } catch (e) {
      return (false, 'Error de conexión: $e');
    }
  }

  /// Registro de nueva cuenta con Correo y Contraseña
  Future<(bool, String)> signUpWithEmail(String email, String password) async {
    try {
      final res = await _client.auth.signUp(
        email: email.trim(),
        password: password,
        emailRedirectTo: AppConfig.oauthRedirectUrl,
      );
      if (res.session != null && res.user != null) {
        return (true, '¡Cuenta creada y conectada (${res.user!.email})!');
      }
      if (res.user != null) {
        return (
          true,
          '¡Cuenta registrada! Revisa tu correo electrónico para confirmar tu cuenta y luego inicia sesión.'
        );
      }
      return (false, 'No se pudo completar el registro.');
    } on AuthException catch (e) {
      return (false, _translateAuthError(e.message));
    } catch (e) {
      return (false, 'Error de red al crear cuenta: $e');
    }
  }

  /// Inicio de sesión con Google OAuth mediante Deep Link nativo (misfinanzas://login-callback)
  Future<(bool, String)> signInWithGoogle() async {
    try {
      final launched = await _client.auth.signInWithOAuth(
        OAuthProvider.google,
        redirectTo: kIsWeb ? null : AppConfig.oauthRedirectUrl,
        authScreenLaunchMode: LaunchMode.externalApplication,
      );
      if (launched) {
        return (true, 'Completa el acceso con Google en el navegador...');
      }
      return (false, 'No se pudo abrir el navegador para iniciar sesión con Google.');
    } on AuthException catch (e) {
      return (false, _translateAuthError(e.message));
    } catch (e) {
      return (false, 'Error al iniciar Google OAuth: $e');
    }
  }

  Future<void> signOut() async {
    try {
      await _client.auth.signOut();
    } catch (_) {}
  }

  String _translateAuthError(String msg) {
    final lower = msg.toLowerCase();
    if (lower.contains('invalid login credentials')) {
      return 'Correo o contraseña incorrectos.';
    }
    if (lower.contains('email not confirmed')) {
      return 'Confirma tu correo electrónico antes de iniciar sesión (revisa tu bandeja de entrada).';
    }
    if (lower.contains('already registered')) {
      return 'Este correo ya está registrado. Usa la opción "Iniciar Sesión".';
    }
    return msg;
  }

  /// Sincronización bidireccional Offline-First con Supabase PostgREST
  Future<SyncResult> syncPendingTransactions() async {
    final uid = userId;
    if (uid == null) {
      return const SyncResult(
        success: false,
        syncedCount: 0,
        message: 'Inicia sesión para respaldar tus finanzas en la nube.',
      );
    }

    if (_isSyncing) {
      return const SyncResult(
        success: false,
        syncedCount: 0,
        message: 'Sincronización en progreso...',
      );
    }

    _isSyncing = true;
    try {
      // 1. Procesar eliminaciones pendientes (evita Gastos Zombie)
      final pendingDeletes = _localStorage.getPendingDeletes();
      final List<String> deletedIds = [];
      for (final delId in pendingDeletes) {
        await _client
            .from('transactions')
            .delete()
            .eq('id', delId)
            .eq('user_id', uid);
        deletedIds.add(delId);
      }
      if (deletedIds.isNotEmpty) {
        await _localStorage.clearFromDeleteQueue(deletedIds);
      }

      // 2. Procesar subidas y ediciones pendientes
      final pendingUpserts = _localStorage.getPendingQueue();
      final List<String> syncedIds = [];
      for (final tx in pendingUpserts) {
        await _client
            .from('transactions')
            .upsert(tx.toSupabasePayload(uid));
        syncedIds.add(tx.id);
      }
      if (syncedIds.isNotEmpty) {
        await _localStorage.clearFromQueue(syncedIds);
      }

      // 3. Descargar estado remoto y unificar por ID sin duplicar
      final List<dynamic> remoteData = await _client
          .from('transactions')
          .select()
          .eq('user_id', uid)
          .order('created_at', ascending: false);

      final remainingDeletes = _localStorage.getPendingDeletes().toSet();
      final Map<String, TransactionModel> unifiedById = {};

      for (final item in remoteData) {
        final rTx = TransactionModel.fromJson(
          item as Map<String, dynamic>,
          forceSynced: true,
        );
        if (!remainingDeletes.contains(rTx.id)) {
          unifiedById[rTx.id] = rTx;
        }
      }

      // Cualquier cambio local pendiente mantiene prioridad
      for (final localPending in _localStorage.getPendingQueue()) {
        unifiedById[localPending.id] = localPending;
      }

      final mergedList = unifiedById.values.toList()
        ..sort((a, b) => b.createdAt.compareTo(a.createdAt));

      await _localStorage.saveTransactions(mergedList);

      return SyncResult(
        success: true,
        syncedCount: syncedIds.length,
        message: 'Nube sincronizada (${mergedList.length} movimientos al día)',
      );
    } catch (e) {
      return SyncResult(
        success: false,
        syncedCount: 0,
        message: 'Modo Offline activo (se sincronizará al recuperar conexión)',
      );
    } finally {
      _isSyncing = false;
    }
  }
}
