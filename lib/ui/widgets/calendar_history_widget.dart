import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:intl/intl.dart';
import 'package:table_calendar/table_calendar.dart';
import '../../config/app_config.dart';
import '../../models/transaction_model.dart';
import 'transaction_card_widget.dart';

class CalendarHistoryWidget extends StatefulWidget {
  final DateTime focusedMonth;
  final DateTime? selectedDate;
  final List<TransactionModel> allTransactions;
  final ValueChanged<DateTime> onMonthChanged;
  final ValueChanged<DateTime?> onDaySelected;
  final ValueChanged<DateTime> onAddForDate;
  final ValueChanged<TransactionModel> onEditTransaction;
  final ValueChanged<TransactionModel> onDeleteTransaction;

  const CalendarHistoryWidget({
    super.key,
    required this.focusedMonth,
    required this.selectedDate,
    required this.allTransactions,
    required this.onMonthChanged,
    required this.onDaySelected,
    required this.onAddForDate,
    required this.onEditTransaction,
    required this.onDeleteTransaction,
  });

  @override
  State<CalendarHistoryWidget> createState() => _CalendarHistoryWidgetState();
}

class _CalendarHistoryWidgetState extends State<CalendarHistoryWidget> {
  CalendarFormat _calendarFormat = CalendarFormat.month;
  String _filterType = 'todos'; // 'todos' | 'gasto' | 'ingreso'
  String _searchQuery = '';
  final TextEditingController _searchController = TextEditingController();

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  List<TransactionModel> _getEventsForDay(DateTime day) {
    return widget.allTransactions.where((tx) => isSameDay(tx.createdAt, day)).toList();
  }

  List<TransactionModel> get _filteredTransactions {
    return widget.allTransactions.where((tx) {
      if (widget.selectedDate != null) {
        if (!isSameDay(tx.createdAt, widget.selectedDate)) return false;
      } else {
        if (tx.createdAt.year != widget.focusedMonth.year ||
            tx.createdAt.month != widget.focusedMonth.month) {
          return false;
        }
      }

      if (_filterType == 'gasto' && !tx.isExpense) return false;
      if (_filterType == 'ingreso' && tx.isExpense) return false;

      if (_searchQuery.isNotEmpty) {
        final q = _searchQuery.toLowerCase();
        final matchCat = tx.category.toLowerCase().contains(q);
        final matchNote = tx.note.toLowerCase().contains(q);
        if (!matchCat && !matchNote) return false;
      }
      return true;
    }).toList();
  }

  Future<void> _exportCsv(List<TransactionModel> items) async {
    if (items.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('No hay movimientos en este filtro para exportar.')),
      );
      return;
    }

    final buffer = StringBuffer('Fecha,Tipo,Categoria,Metodo,Nota,Monto\n');
    for (final tx in items) {
      final dateStr = DateFormat('yyyy-MM-dd').format(tx.createdAt);
      final safeNote = tx.cleanNote.replaceAll('"', '""');
      buffer.writeln(
        '$dateStr,${tx.type},"${tx.category}","${tx.paymentMethod}","$safeNote",${tx.amount.toStringAsFixed(2)}',
      );
    }

    await Clipboard.setData(ClipboardData(text: buffer.toString()));
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('CSV copiado al portapapeles (${items.length} movimientos). Pégalo en Excel o WhatsApp.'),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final fmt = NumberFormat('#,##0.00', 'en_US');
    final filtered = _filteredTransactions;

    // Agrupar por fecha (yyyy-MM-dd)
    final Map<String, List<TransactionModel>> groupedByDate = {};
    for (final tx in filtered) {
      final key = DateFormat('yyyy-MM-dd').format(tx.createdAt);
      groupedByDate.putIfAbsent(key, () => []).add(tx);
    }
    final sortedKeys = groupedByDate.keys.toList()..sort((a, b) => b.compareTo(a));

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Calendario Mensual Interactivo
        Container(
          decoration: BoxDecoration(
            color: colorScheme.surfaceContainerHighest.withOpacity(0.55),
            borderRadius: BorderRadius.circular(18),
            border: Border.all(color: colorScheme.outlineVariant.withOpacity(0.4)),
          ),
          padding: const EdgeInsets.fromLTRB(8, 4, 8, 12),
          child: Column(
            children: [
              TableCalendar<TransactionModel>(
                locale: 'es_ES',
                firstDay: DateTime(2020, 1, 1),
                lastDay: DateTime(2035, 12, 31),
                focusedDay: widget.focusedMonth,
                calendarFormat: _calendarFormat,
                startingDayOfWeek: StartingDayOfWeek.monday,
                selectedDayPredicate: (day) =>
                    widget.selectedDate != null && isSameDay(widget.selectedDate, day),
                eventLoader: _getEventsForDay,
                availableCalendarFormats: const {
                  CalendarFormat.month: 'Mes',
                  CalendarFormat.twoWeeks: '2 Sem',
                  CalendarFormat.week: 'Semana',
                },
                onFormatChanged: (format) {
                  setState(() {
                    _calendarFormat = format;
                  });
                },
                onDaySelected: (selectedDay, focusedDay) {
                  if (widget.selectedDate != null && isSameDay(widget.selectedDate, selectedDay)) {
                    widget.onDaySelected(null);
                  } else {
                    widget.onDaySelected(selectedDay);
                  }
                },
                onPageChanged: (focusedDay) {
                  widget.onMonthChanged(focusedDay);
                },
                headerStyle: HeaderStyle(
                  titleCentered: true,
                  formatButtonDecoration: BoxDecoration(
                    border: Border.all(color: colorScheme.outlineVariant),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  formatButtonTextStyle: TextStyle(fontSize: 11, color: colorScheme.onSurface),
                  titleTextStyle: const TextStyle(fontSize: 15, fontWeight: FontWeight.bold),
                ),
                calendarStyle: CalendarStyle(
                  outsideDaysVisible: false,
                  todayDecoration: BoxDecoration(
                    color: colorScheme.primary.withOpacity(0.25),
                    shape: BoxShape.circle,
                  ),
                  selectedDecoration: BoxDecoration(
                    color: colorScheme.primary,
                    shape: BoxShape.circle,
                  ),
                ),
                calendarBuilders: CalendarBuilders(
                  markerBuilder: (context, date, events) {
                    if (events.isEmpty) return const SizedBox.shrink();
                    final hasIncome = events.any((e) => !e.isExpense);
                    final hasExpense = events.any((e) => e.isExpense);
                    return Positioned(
                      bottom: 4,
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          if (hasIncome)
                            Container(
                              width: 6,
                              height: 6,
                              margin: const EdgeInsets.symmetric(horizontal: 1.5),
                              decoration: const BoxDecoration(
                                color: Color(0xFF2DD4BF),
                                shape: BoxShape.circle,
                              ),
                            ),
                          if (hasExpense)
                            Container(
                              width: 6,
                              height: 6,
                              margin: const EdgeInsets.symmetric(horizontal: 1.5),
                              decoration: const BoxDecoration(
                                color: Color(0xFFF87171),
                                shape: BoxShape.circle,
                              ),
                            ),
                        ],
                      ),
                    );
                  },
                ),
              ),
              const SizedBox(height: 6),
              if (widget.selectedDate != null)
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 8),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Flexible(
                        child: Text(
                          'Día: ${DateFormat('dd/MM/yyyy').format(widget.selectedDate!)}',
                          style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.bold),
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                      Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          TextButton(
                            onPressed: () => widget.onDaySelected(null),
                            child: const Text('Ver todo el mes', style: TextStyle(fontSize: 12)),
                          ),
                          FilledButton.tonalIcon(
                            onPressed: () => widget.onAddForDate(widget.selectedDate!),
                            icon: const Icon(Icons.add_rounded, size: 16),
                            label: const Text('Añadir aquí', style: TextStyle(fontSize: 12)),
                          ),
                        ],
                      ),
                    ],
                  ),
                )
              else
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 10),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Row(
                        children: [
                          Container(
                            width: 8,
                            height: 8,
                            decoration: const BoxDecoration(
                              color: Color(0xFF2DD4BF),
                              shape: BoxShape.circle,
                            ),
                          ),
                          const SizedBox(width: 4),
                          const Text('Ingreso', style: TextStyle(fontSize: 11)),
                          const SizedBox(width: 10),
                          Container(
                            width: 8,
                            height: 8,
                            decoration: const BoxDecoration(
                              color: Color(0xFFF87171),
                              shape: BoxShape.circle,
                            ),
                          ),
                          const SizedBox(width: 4),
                          const Text('Gasto', style: TextStyle(fontSize: 11)),
                        ],
                      ),
                      Text(
                        'Toca un día para filtrar',
                        style: TextStyle(fontSize: 11, color: colorScheme.onSurfaceVariant),
                      ),
                    ],
                  ),
                ),
            ],
          ),
        ),
        const SizedBox(height: 12),
        // Buscador
        TextField(
          controller: _searchController,
          decoration: InputDecoration(
            hintText: 'Buscar por nota, categoría o método...',
            prefixIcon: const Icon(Icons.search_rounded, size: 20),
            suffixIcon: _searchQuery.isNotEmpty
                ? IconButton(
                    icon: const Icon(Icons.clear_rounded, size: 18),
                    onPressed: () {
                      _searchController.clear();
                      setState(() {
                        _searchQuery = '';
                      });
                    },
                  )
                : null,
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(14)),
            contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
          ),
          onChanged: (value) {
            setState(() {
              _searchQuery = value.trim();
            });
          },
        ),
        const SizedBox(height: 10),
        // Filtros y Exportar CSV
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Wrap(
              spacing: 6,
              children: [
                ChoiceChip(
                  label: const Text('Todos', style: TextStyle(fontSize: 11.5)),
                  selected: _filterType == 'todos',
                  visualDensity: VisualDensity.compact,
                  onSelected: (_) => setState(() => _filterType = 'todos'),
                ),
                ChoiceChip(
                  label: const Text('Gastos', style: TextStyle(fontSize: 11.5)),
                  selected: _filterType == 'gasto',
                  visualDensity: VisualDensity.compact,
                  onSelected: (_) => setState(() => _filterType = 'gasto'),
                ),
                ChoiceChip(
                  label: const Text('Ingresos', style: TextStyle(fontSize: 11.5)),
                  selected: _filterType == 'ingreso',
                  visualDensity: VisualDensity.compact,
                  onSelected: (_) => setState(() => _filterType = 'ingreso'),
                ),
              ],
            ),
            TextButton.icon(
              onPressed: () => _exportCsv(filtered),
              icon: const Icon(Icons.download_outlined, size: 17),
              label: const Text('CSV', style: TextStyle(fontSize: 12)),
            ),
          ],
        ),
        const SizedBox(height: 8),
        if (sortedKeys.isEmpty)
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(24),
            decoration: BoxDecoration(
              color: colorScheme.surfaceContainerHighest.withOpacity(0.45),
              borderRadius: BorderRadius.circular(14),
            ),
            child: Column(
              children: [
                Icon(Icons.history_toggle_off_rounded, size: 34, color: colorScheme.onSurfaceVariant),
                const SizedBox(height: 6),
                Text(
                  'No hay movimientos en esta fecha o filtro.',
                  style: TextStyle(fontSize: 13, color: colorScheme.onSurfaceVariant),
                ),
              ],
            ),
          )
        else
          ...sortedKeys.map((dateKey) {
            final dayItems = groupedByDate[dateKey]!;
            final dayInc = dayItems.where((t) => !t.isExpense).fold(0.0, (s, t) => s + t.amount);
            final dayExp = dayItems.where((t) => t.isExpense).fold(0.0, (s, t) => s + t.amount);
            final dayNet = dayInc - dayExp;
            final netPrefix = dayNet >= 0 ? '+' : '';
            final parsedDay = DateTime.parse(dateKey);

            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Padding(
                  padding: const EdgeInsets.fromLTRB(4, 8, 4, 6),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        DateFormat('EEEE, dd MMM yyyy', 'es_ES').format(parsedDay),
                        style: TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.bold,
                          color: colorScheme.onSurfaceVariant,
                        ),
                      ),
                      Text(
                        'Neto día: $netPrefix${AppConfig.currencySymbol} ${fmt.format(dayNet)}',
                        style: TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.bold,
                          color: dayNet >= 0 ? const Color(0xFF2DD4BF) : const Color(0xFFF87171),
                        ),
                      ),
                    ],
                  ),
                ),
                ...dayItems.map(
                  (tx) => TransactionCardWidget(
                    transaction: tx,
                    onEdit: () => widget.onEditTransaction(tx),
                    onDelete: () => widget.onDeleteTransaction(tx),
                  ),
                ),
              ],
            );
          }),
      ],
    );
  }
}
