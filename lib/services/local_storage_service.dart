import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:uuid/uuid.dart';
import '../models/transaction_model.dart';

class LocalStorageService {
  static const String _transactionsKey = 'finanzas_transactions_cache';
  static const String _pendingQueueKey = 'finanzas_pending_sync_queue';
  static const String _pendingDeleteKey = 'finanzas_pending_delete_queue';
  static const String _darkModeKey = 'finanzas_dark_mode';

  final SharedPreferences _prefs;
  final Uuid _uuid = const Uuid();

  LocalStorageService(this._prefs);

  bool get isDarkMode => _prefs.getBool(_darkModeKey) ?? true;

  Future<void> setDarkMode(bool value) async {
    await _prefs.setBool(_darkModeKey, value);
  }

  List<TransactionModel> getTransactions() {
    final raw = _prefs.getString(_transactionsKey);
    if (raw == null || raw.isEmpty) return [];
    try {
      final List<dynamic> decoded = jsonDecode(raw) as List<dynamic>;
      final list = decoded
          .map((item) => TransactionModel.fromJson(item as Map<String, dynamic>))
          .toList();
      list.sort((a, b) => b.createdAt.compareTo(a.createdAt));
      return list;
    } catch (_) {
      return [];
    }
  }

  Future<void> saveTransactions(List<TransactionModel> transactions) async {
    transactions.sort((a, b) => b.createdAt.compareTo(a.createdAt));
    final encoded = jsonEncode(transactions.map((t) => t.toJson()).toList());
    await _prefs.setString(_transactionsKey, encoded);
  }

  Future<TransactionModel> addTransactionLocal({
    required String type,
    required double amount,
    required String category,
    required String note,
    required String userId,
    DateTime? createdAt,
  }) async {
    final newTx = TransactionModel(
      id: _uuid.v4(),
      userId: userId,
      type: type,
      amount: double.parse(amount.toStringAsFixed(2)),
      category: category,
      note: note,
      createdAt: createdAt ?? DateTime.now(),
      synced: false,
    );

    final transactions = getTransactions();
    transactions.insert(0, newTx);
    await saveTransactions(transactions);

    final queue = getPendingQueue().where((q) => q.id != newTx.id).toList();
    queue.add(newTx);
    await _savePendingQueue(queue);
    return newTx;
  }

  Future<void> updateTransactionLocal({
    required String id,
    required String type,
    required double amount,
    required String category,
    required String note,
    DateTime? createdAt,
  }) async {
    final transactions = getTransactions();
    TransactionModel? updatedTx;

    final updatedList = transactions.map((tx) {
      if (tx.id == id) {
        updatedTx = tx.copyWith(
          type: type,
          amount: double.parse(amount.toStringAsFixed(2)),
          category: category,
          note: note,
          createdAt: createdAt ?? tx.createdAt,
          synced: false,
        );
        return updatedTx!;
      }
      return tx;
    }).toList();

    await saveTransactions(updatedList);

    if (updatedTx != null) {
      final queue = getPendingQueue().where((q) => q.id != id).toList();
      queue.add(updatedTx!);
      await _savePendingQueue(queue);
    }
  }

  Future<void> deleteTransactionLocal(String id) async {
    final transactions = getTransactions();
    final target = transactions.where((tx) => tx.id == id).firstOrNull;

    final remaining = transactions.where((tx) => tx.id != id).toList();
    await saveTransactions(remaining);

    final queue = getPendingQueue().where((tx) => tx.id != id).toList();
    await _savePendingQueue(queue);

    if (target == null || target.synced) {
      final delQueue = getPendingDeletes();
      if (!delQueue.contains(id)) {
        delQueue.add(id);
        await _prefs.setString(_pendingDeleteKey, jsonEncode(delQueue));
      }
    }
  }

  List<TransactionModel> getPendingQueue() {
    final raw = _prefs.getString(_pendingQueueKey);
    if (raw == null || raw.isEmpty) return [];
    try {
      final List<dynamic> decoded = jsonDecode(raw) as List<dynamic>;
      return decoded
          .map((item) => TransactionModel.fromJson(item as Map<String, dynamic>))
          .toList();
    } catch (_) {
      return [];
    }
  }

  Future<void> _savePendingQueue(List<TransactionModel> queue) async {
    final encoded = jsonEncode(queue.map((t) => t.toJson()).toList());
    await _prefs.setString(_pendingQueueKey, encoded);
  }

  List<String> getPendingDeletes() {
    final raw = _prefs.getString(_pendingDeleteKey);
    if (raw == null || raw.isEmpty) return [];
    try {
      final List<dynamic> decoded = jsonDecode(raw) as List<dynamic>;
      return decoded.map((e) => e.toString()).toList();
    } catch (_) {
      return [];
    }
  }

  Future<void> clearFromDeleteQueue(List<String> deletedIds) async {
    final remaining = getPendingDeletes().where((id) => !deletedIds.contains(id)).toList();
    await _prefs.setString(_pendingDeleteKey, jsonEncode(remaining));
  }

  Future<void> clearFromQueue(List<String> syncedIds) async {
    final queue = getPendingQueue().where((tx) => !syncedIds.contains(tx.id)).toList();
    await _savePendingQueue(queue);

    final transactions = getTransactions().map((tx) {
      if (syncedIds.contains(tx.id)) {
        return tx.copyWith(synced: true);
      }
      return tx;
    }).toList();
    await saveTransactions(transactions);
  }

  int get totalPendingCount => getPendingQueue().length + getPendingDeletes().length;
}
