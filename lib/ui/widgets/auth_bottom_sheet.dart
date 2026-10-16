import 'package:flutter/material.dart';
import '../../services/supabase_sync_service.dart';

class AuthBottomSheet extends StatefulWidget {
  final SupabaseSyncService supabaseService;
  final VoidCallback onSyncRequested;
  final VoidCallback onAuthChanged;

  const AuthBottomSheet({
    super.key,
    required this.supabaseService,
    required this.onSyncRequested,
    required this.onAuthChanged,
  });

  @override
  State<AuthBottomSheet> createState() => _AuthBottomSheetState();
}

class _AuthBottomSheetState extends State<AuthBottomSheet> {
  String _mode = 'login'; // 'login' | 'signup'
  bool _obscurePassword = true;
  bool _isLoading = false;
  String? _feedbackMessage;
  bool _isFeedbackSuccess = false;

  final TextEditingController _emailController = TextEditingController();
  final TextEditingController _passwordController = TextEditingController();

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _handleEmailSubmit() async {
    final email = _emailController.text.trim();
    final password = _passwordController.text;

    if (email.isEmpty || password.length < 6) {
      setState(() {
        _feedbackMessage = 'Ingresa un correo válido y una contraseña de al menos 6 caracteres.';
        _isFeedbackSuccess = false;
      });
      return;
    }

    setState(() {
      _isLoading = true;
      _feedbackMessage = null;
    });

    final (ok, msg) = _mode == 'login'
        ? await widget.supabaseService.signInWithEmail(email, password)
        : await widget.supabaseService.signUpWithEmail(email, password);

    if (!mounted) return;
    setState(() {
      _isLoading = false;
      _feedbackMessage = msg;
      _isFeedbackSuccess = ok;
    });

    if (ok && widget.supabaseService.isLoggedIn) {
      widget.onAuthChanged();
      Navigator.of(context).pop();
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg)));
    }
  }

  Future<void> _handleGoogleLogin() async {
    setState(() {
      _isLoading = true;
      _feedbackMessage = null;
    });

    final (ok, msg) = await widget.supabaseService.signInWithGoogle();
    if (!mounted) return;
    setState(() {
      _isLoading = false;
      _feedbackMessage = msg;
      _isFeedbackSuccess = ok;
    });
  }

  Future<void> _handleLogout() async {
    await widget.supabaseService.signOut();
    widget.onAuthChanged();
    if (!mounted) return;
    Navigator.of(context).pop();
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Sesión cerrada correctamente')),
    );
  }

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final bottomInset = MediaQuery.of(context).viewInsets.bottom;
    final isLoggedIn = widget.supabaseService.isLoggedIn;
    final email = widget.supabaseService.userEmail ?? 'Usuario conectado';

    return Padding(
      padding: EdgeInsets.only(bottom: bottomInset),
      child: SafeArea(
        top: false,
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 22),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Center(
                child: Container(
                  width: 40,
                  height: 4,
                  margin: const EdgeInsets.only(bottom: 12),
                  decoration: BoxDecoration(
                    color: colorScheme.outlineVariant,
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Row(
                    children: [
                      Icon(Icons.cloud_sync_rounded, color: colorScheme.primary),
                      const SizedBox(width: 8),
                      const Text(
                        'Cuenta y Respaldo en la Nube',
                        style: TextStyle(fontSize: 17, fontWeight: FontWeight.bold),
                      ),
                    ],
                  ),
                  IconButton(
                    icon: const Icon(Icons.close_rounded),
                    onPressed: () => Navigator.of(context).pop(),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              if (isLoggedIn) ...[
                Container(
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: colorScheme.surfaceContainerHighest.withOpacity(0.55),
                    borderRadius: BorderRadius.circular(14),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.verified_user_rounded, color: Color(0xFF10B981), size: 28),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Sesión activa en Supabase',
                              style: TextStyle(fontSize: 12, color: colorScheme.onSurfaceVariant),
                            ),
                            Text(
                              email,
                              style: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold),
                              overflow: TextOverflow.ellipsis,
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 14),
                Row(
                  children: [
                    Expanded(
                      child: FilledButton.tonalIcon(
                        onPressed: () {
                          Navigator.of(context).pop();
                          widget.onSyncRequested();
                        },
                        icon: const Icon(Icons.sync_rounded),
                        label: const Text('Sincronizar'),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: FilledButton.icon(
                        style: FilledButton.styleFrom(
                          backgroundColor: const Color(0xFFF87171),
                          foregroundColor: Colors.white,
                        ),
                        onPressed: _handleLogout,
                        icon: const Icon(Icons.logout_rounded),
                        label: const Text('Cerrar Sesión'),
                      ),
                    ),
                  ],
                ),
              ] else ...[
                Text(
                  'Conecta tu cuenta con Correo y Contraseña o con Google para respaldar tus movimientos en la nube.',
                  style: TextStyle(fontSize: 12, color: colorScheme.onSurfaceVariant),
                ),
                const SizedBox(height: 12),
                SizedBox(
                  width: double.infinity,
                  child: SegmentedButton<String>(
                    segments: const [
                      ButtonSegment(
                        value: 'login',
                        label: Text('Iniciar Sesión'),
                        icon: Icon(Icons.login_rounded, size: 18),
                      ),
                      ButtonSegment(
                        value: 'signup',
                        label: Text('Crear Cuenta'),
                        icon: Icon(Icons.person_add_alt_1_rounded, size: 18),
                      ),
                    ],
                    selected: {_mode},
                    onSelectionChanged: (s) {
                      setState(() {
                        _mode = s.first;
                        _feedbackMessage = null;
                      });
                    },
                  ),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: _emailController,
                  keyboardType: TextInputType.emailAddress,
                  decoration: InputDecoration(
                    labelText: 'Correo electrónico',
                    prefixIcon: const Icon(Icons.email_outlined),
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(14)),
                    contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                  ),
                ),
                const SizedBox(height: 10),
                TextField(
                  controller: _passwordController,
                  obscureText: _obscurePassword,
                  decoration: InputDecoration(
                    labelText: 'Contraseña (mín. 6 caracteres)',
                    prefixIcon: const Icon(Icons.lock_outline_rounded),
                    suffixIcon: IconButton(
                      icon: Icon(
                        _obscurePassword ? Icons.visibility_outlined : Icons.visibility_off_outlined,
                      ),
                      onPressed: () {
                        setState(() {
                          _obscurePassword = !_obscurePassword;
                        });
                      },
                    ),
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(14)),
                    contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                  ),
                  onSubmitted: (_) => _handleEmailSubmit(),
                ),
                if (_isLoading) ...[
                  const SizedBox(height: 10),
                  const LinearProgressIndicator(),
                ],
                if (_feedbackMessage != null) ...[
                  const SizedBox(height: 10),
                  Text(
                    _feedbackMessage!,
                    style: TextStyle(
                      fontSize: 12,
                      color: _isFeedbackSuccess ? const Color(0xFF10B981) : const Color(0xFFF87171),
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
                const SizedBox(height: 12),
                SizedBox(
                  width: double.infinity,
                  height: 46,
                  child: FilledButton.icon(
                    onPressed: _isLoading ? null : _handleEmailSubmit,
                    icon: const Icon(Icons.arrow_forward_rounded),
                    label: Text(_mode == 'login' ? 'Ingresar con Correo' : 'Registrar Cuenta Gratis'),
                  ),
                ),
                const Padding(
                  padding: EdgeInsets.symmetric(vertical: 10),
                  child: Divider(height: 1),
                ),
                SizedBox(
                  width: double.infinity,
                  height: 46,
                  child: OutlinedButton.icon(
                    onPressed: _isLoading ? null : _handleGoogleLogin,
                    icon: const Icon(Icons.account_circle_outlined),
                    label: const Text('Continuar con Google'),
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
