import 'dart:async';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import '../../config/app_config.dart';
import '../../models/transaction_model.dart';
import '../../services/local_storage_service.dart';
import '../../services/supabase_sync_service.dart';
import '../widgets/auth_bottom_sheet.dart';
import '../widgets/calendar_history_widget.dart';
import '../widgets/charts_widget.dart';
import '../widgets/summary_cards_widget.dart';
import '../widgets/transaction_bottom_sheet.dart';
import '../widgets/transaction_card_widget.dart';

class HomeScreen extends StatefulWidget {
  final LocalStorageService localStorage;
  final SupabaseSyncService supabaseService;
  final VoidCallback onToggleTheme;
  final bool isDarkMode;

  const HomeScreen({
    super.key,
    required this.localStorage,
    required this.supabaseService,
    required this.onToggleTheme,
    required this.isDarkMode,
  });

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _selectedTabIndex = 0;
  DateTime _focusedMonth = DateTime(DateTime.now().year, DateTime.now().month, 1);
  DateTime? _selectedCalendarDay;
  List<TransactionModel> _transactions = [];
  StreamSubscription<AuthState>? _authSubscription;

  @override
  void initState() {
    super.initState();
    _loadLocalData();

    // Escuchar cambios de sesión OAuth / Email en tiempo real (incluyendo retorno de Deep Link)
    _authSubscription = widget.supabaseService.authStateChanges.listen((data) {
      if (!mounted) return;
      setState(() {});
      if (data.event == AuthChangeEvent.signedIn ||
          data.event == AuthChangeEvent.tokenRefreshed) {
        _syncInBackground(notifyUser: data.event == AuthChangeEvent.signedIn);
      }
    });

    if (widget.supabaseService.isLoggedIn) {
      _syncInBackground(notifyUser: false);
    }
  }

  @override
  void dispose() {
    _authSubscription?.cancel();
    super.dispose();
  }

  void _loadLocalData() {
    setState(() {
      _transactions = widget.localStorage.getTransactions();
    });
  }

  Future<void> _syncInBackground({bool notifyUser = false}) async {
    final res = await widget.supabaseService.syncPendingTransactions();
    if (!mounted) return;
    _loadLocalData();
    if (notifyUser) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(res.message), duration: const Duration(seconds: 2)),
      );
    }
  }

  void _changeMonth(int deltaMonths) {
    setState(() {
      _focusedMonth = DateTime(_focusedMonth.year, _focusedMonth.month + deltaMonths, 1);
      _selectedCalendarDay = null;
    });
  }

  void _openTransactionSheet({
    TransactionModel? editingTx,
    String initialType = 'gasto',
    DateTime? initialDate,
  }) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (ctx) => TransactionBottomSheet(
        editingTransaction: editingTx,
        initialType: initialType,
        initialDate: initialDate ?? _selectedCalendarDay,
        onSave: ({
          String? id,
          required String type,
          required double amount,
          required String category,
          required String note,
          required DateTime createdAt,
        }) async {
          final uid = widget.supabaseService.userId ?? 'local_user';
          if (id == null) {
            await widget.localStorage.addTransactionLocal(
              type: type,
              amount: amount,
              category: category,
              note: note,
              userId: uid,
              createdAt: createdAt,
            );
          } else {
            await widget.localStorage.updateTransactionLocal(
              id: id,
              type: type,
              amount: amount,
              category: category,
              note: note,
              createdAt: createdAt,
            );
          }

          setState(() {
            _focusedMonth = DateTime(createdAt.year, createdAt.month, 1);
          });
          _loadLocalData();
          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(
                content: Text(id == null ? 'Movimiento registrado' : 'Movimiento actualizado'),
                duration: const Duration(milliseconds: 1500),
              ),
            );
          }
          await _syncInBackground(notifyUser: false);
        },
      ),
    );
  }

  void _openAuthSheet() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (ctx) => AuthBottomSheet(
        supabaseService: widget.supabaseService,
        onSyncRequested: () => _syncInBackground(notifyUser: true),
        onAuthChanged: () {
          _loadLocalData();
          _syncInBackground(notifyUser: true);
        },
      ),
    );
  }

  Future<void> _confirmDelete(TransactionModel tx) async {
    final fmt = NumberFormat('#,##0.00', 'en_US');
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Row(
          children: [
            Icon(Icons.warning_amber_rounded, color: Color(0xFFF87171)),
            SizedBox(width: 8),
            Expanded(
              child: Text(
                'Confirmar eliminación',
                style: TextStyle(fontSize: 17, fontWeight: FontWeight.bold),
              ),
            ),
          ],
        ),
        content: Text(
          '¿Deseas eliminar este ${tx.isExpense ? "gasto" : "ingreso"} de ${tx.category} por ${AppConfig.currencySymbol} ${fmt.format(tx.amount)}?\n\nEsta acción no se puede deshacer.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text('Cancelar'),
          ),
          FilledButton.icon(
            style: FilledButton.styleFrom(
              backgroundColor: const Color(0xFFF87171),
              foregroundColor: Colors.white,
            ),
            onPressed: () => Navigator.of(ctx).pop(true),
            icon: const Icon(Icons.delete_forever_rounded),
            label: const Text('Eliminar'),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      await widget.localStorage.deleteTransactionLocal(tx.id);
      _loadLocalData();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Movimiento eliminado'),
            duration: Duration(milliseconds: 1500),
          ),
        );
      }
      await _syncInBackground(notifyUser: false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final allIncome = _transactions
        .where((t) => !t.isExpense)
        .fold(0.0, (sum, t) => sum + t.amount);
    final allExpense = _transactions
        .where((t) => t.isExpense)
        .fold(0.0, (sum, t) => sum + t.amount);
    final allTimeBalance = allIncome - allExpense;

    final monthlyTransactions = _transactions
        .where((t) =>
            t.createdAt.year == _focusedMonth.year &&
            t.createdAt.month == _focusedMonth.month)
        .toList();
    final monthlyIncome = monthlyTransactions
        .where((t) => !t.isExpense)
        .fold(0.0, (sum, t) => sum + t.amount);
    final monthlyExpense = monthlyTransactions
        .where((t) => t.isExpense)
        .fold(0.0, (sum, t) => sum + t.amount);

    final monthLabel =
        '${AppConfig.shortMonthNames[_focusedMonth.month]} ${_focusedMonth.year}';
    final fullMonthLabel =
        '${AppConfig.fullMonthNames[_focusedMonth.month]} ${_focusedMonth.year}';
    final userEmail = widget.supabaseService.userEmail;
    final accountLabel = userEmail != null && userEmail.isNotEmpty
        ? userEmail.split('@').first
        : 'Cuenta';

    return Scaffold(
      appBar: AppBar(
        title: const Text(
          'Mis Finanzas (S/)',
          style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.sync_rounded),
            tooltip: 'Sincronizar con la nube',
            onPressed: () {
              if (!widget.supabaseService.isLoggedIn) {
                _openAuthSheet();
              } else {
                _syncInBackground(notifyUser: true);
              }
            },
          ),
          IconButton(
            icon: Icon(
              widget.isDarkMode ? Icons.light_mode_outlined : Icons.dark_mode_outlined,
            ),
            tooltip: 'Cambiar tema',
            onPressed: widget.onToggleTheme,
          ),
          Padding(
            padding: const EdgeInsets.only(right: 10),
            child: FilledButton.tonalIcon(
              style: FilledButton.styleFrom(
                visualDensity: VisualDensity.compact,
                padding: const EdgeInsets.symmetric(horizontal: 10),
              ),
              onPressed: _openAuthSheet,
              icon: Icon(
                widget.supabaseService.isLoggedIn
                    ? Icons.verified_user_rounded
                    : Icons.account_circle_outlined,
                size: 17,
              ),
              label: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 75),
                child: Text(
                  accountLabel,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontSize: 12),
                ),
              ),
            ),
          ),
        ],
      ),
      body: SafeArea(
        child: Column(
          children: [
            Expanded(
              child: RefreshIndicator(
                onRefresh: () => _syncInBackground(notifyUser: true),
                child: ListView(
                  padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
                  children: [
                    if (_selectedTabIndex == 0) ...[
                      // Barra selectora de Mes / Año
                      Container(
                        margin: const EdgeInsets.only(bottom: 12),
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                        decoration: BoxDecoration(
                          color: colorScheme.surfaceContainerHighest.withOpacity(0.55),
                          borderRadius: BorderRadius.circular(14),
                        ),
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            IconButton(
                              visualDensity: VisualDensity.compact,
                              icon: const Icon(Icons.chevron_left_rounded),
                              onPressed: () => _changeMonth(-1),
                            ),
                            Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Icon(
                                  Icons.calendar_today_rounded,
                                  size: 15,
                                  color: colorScheme.primary,
                                ),
                                const SizedBox(width: 6),
                                Text(
                                  fullMonthLabel,
                                  style: const TextStyle(
                                    fontSize: 14,
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                              ],
                            ),
                            IconButton(
                              visualDensity: VisualDensity.compact,
                              icon: const Icon(Icons.chevron_right_rounded),
                              onPressed: () => _changeMonth(1),
                            ),
                          ],
                        ),
                      ),
                      SummaryCardsWidget(
                        allTimeBalance: allTimeBalance,
                        monthlyIncome: monthlyIncome,
                        monthlyExpense: monthlyExpense,
                        pendingCount: widget.localStorage.totalPendingCount,
                        monthLabel: monthLabel,
                      ),
                      const SizedBox(height: 14),
                      Budget503020Card(
                        transactions: monthlyTransactions,
                        monthlyIncome: monthlyIncome,
                      ),
                      const SizedBox(height: 14),
                      ExpensePieChartCard(transactions: monthlyTransactions),
                      const SizedBox(height: 14),
                      CashflowBarChartCard(
                        monthlyIncome: monthlyIncome,
                        monthlyExpense: monthlyExpense,
                      ),
                      const SizedBox(height: 16),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text(
                            'Movimientos de $monthLabel',
                            style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                          ),
                          TextButton(
                            onPressed: () {
                              setState(() {
                                _selectedTabIndex = 1;
                              });
                            },
                            child: const Text('Ver Calendario →'),
                          ),
                        ],
                      ),
                      const SizedBox(height: 6),
                      if (monthlyTransactions.isEmpty)
                        Container(
                          padding: const EdgeInsets.all(20),
                          decoration: BoxDecoration(
                            color: colorScheme.surfaceContainerHighest.withOpacity(0.45),
                            borderRadius: BorderRadius.circular(14),
                          ),
                          child: Text(
                            'Sin movimientos en $monthLabel. Usa los botones inferiores para registrar tus ingresos o gastos.',
                            textAlign: TextAlign.center,
                            style: TextStyle(fontSize: 12.5, color: colorScheme.onSurfaceVariant),
                          ),
                        )
                      else
                        ...monthlyTransactions.take(8).map(
                              (tx) => TransactionCardWidget(
                                transaction: tx,
                                onEdit: () => _openTransactionSheet(editingTx: tx),
                                onDelete: () => _confirmDelete(tx),
                              ),
                            ),
                    ] else ...[
                      CalendarHistoryWidget(
                        focusedMonth: _focusedMonth,
                        selectedDate: _selectedCalendarDay,
                        allTransactions: _transactions,
                        onMonthChanged: (newMonth) {
                          setState(() {
                            _focusedMonth = DateTime(newMonth.year, newMonth.month, 1);
                            _selectedCalendarDay = null;
                          });
                        },
                        onDaySelected: (day) {
                          setState(() {
                            _selectedCalendarDay = day;
                          });
                        },
                        onAddForDate: (date) {
                          _openTransactionSheet(initialType: 'gasto', initialDate: date);
                        },
                        onEditTransaction: (tx) => _openTransactionSheet(editingTx: tx),
                        onDeleteTransaction: _confirmDelete,
                      ),
                    ],
                  ],
                ),
              ),
            ),
            // Barra fija de acción rápida (- Gasto / + Ingreso)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
              decoration: BoxDecoration(
                color: colorScheme.surface,
                border: Border(
                  top: BorderSide(color: colorScheme.outlineVariant.withOpacity(0.5)),
                ),
              ),
              child: Row(
                children: [
                  Expanded(
                    child: FilledButton.icon(
                      style: FilledButton.styleFrom(
                        backgroundColor: const Color(0xFFF87171),
                        foregroundColor: Colors.white,
                        minimumSize: const Size.fromHeight(44),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                      ),
                      onPressed: () => _openTransactionSheet(initialType: 'gasto'),
                      icon: const Icon(Icons.remove_circle_outline_rounded),
                      label: const Text('- Gasto', style: TextStyle(fontWeight: FontWeight.bold)),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: FilledButton.icon(
                      style: FilledButton.styleFrom(
                        backgroundColor: const Color(0xFF0D9488),
                        foregroundColor: Colors.white,
                        minimumSize: const Size.fromHeight(44),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                      ),
                      onPressed: () => _openTransactionSheet(initialType: 'ingreso'),
                      icon: const Icon(Icons.add_circle_outline_rounded),
                      label: const Text('+ Ingreso', style: TextStyle(fontWeight: FontWeight.bold)),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
      bottomNavigationBar: NavigationBar(
        height: 64,
        selectedIndex: _selectedTabIndex,
        onDestinationSelected: (idx) {
          setState(() {
            _selectedTabIndex = idx;
          });
        },
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.dashboard_outlined),
            selectedIcon: Icon(Icons.dashboard_rounded),
            label: 'Resumen',
          ),
          NavigationDestination(
            icon: Icon(Icons.calendar_month_outlined),
            selectedIcon: Icon(Icons.calendar_month_rounded),
            label: 'Calendario e Historial',
          ),
        ],
      ),
    );
  }
}
