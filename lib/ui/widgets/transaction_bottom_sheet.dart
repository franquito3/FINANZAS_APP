import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../../config/app_config.dart';
import '../../models/transaction_model.dart';

class TransactionBottomSheet extends StatefulWidget {
  final TransactionModel? editingTransaction;
  final String initialType;
  final DateTime? initialDate;
  final Future<void> Function({
    String? id,
    required String type,
    required double amount,
    required String category,
    required String note,
    required DateTime createdAt,
  }) onSave;

  const TransactionBottomSheet({
    super.key,
    this.editingTransaction,
    this.initialType = 'gasto',
    this.initialDate,
    required this.onSave,
  });

  @override
  State<TransactionBottomSheet> createState() => _TransactionBottomSheetState();
}

class _TransactionBottomSheetState extends State<TransactionBottomSheet> {
  late String _selectedType;
  late String _selectedCategory;
  late String _selectedPayment;
  late DateTime _selectedDate;
  final TextEditingController _amountController = TextEditingController();
  final TextEditingController _noteController = TextEditingController();
  String? _amountError;

  @override
  void initState() {
    super.initState();
    final tx = widget.editingTransaction;
    if (tx != null) {
      _selectedType = tx.type;
      _selectedCategory = tx.category;
      _selectedPayment = tx.paymentMethod;
      _selectedDate = tx.createdAt;
      _amountController.text = tx.amount.toStringAsFixed(2);
      _noteController.text = tx.cleanNote;
    } else {
      _selectedType = widget.initialType;
      final cats = _selectedType == 'gasto'
          ? AppConfig.expenseCategories.keys
          : AppConfig.incomeCategories.keys;
      _selectedCategory = cats.first;
      _selectedPayment = AppConfig.paymentMethods.first;
      _selectedDate = widget.initialDate ?? DateTime.now();
    }
  }

  @override
  void dispose() {
    _amountController.dispose();
    _noteController.dispose();
    super.dispose();
  }

  Map<String, CategoryMeta> get _currentCategories =>
      _selectedType == 'gasto' ? AppConfig.expenseCategories : AppConfig.incomeCategories;

  void _setQuickDate(int offsetDays) {
    final now = DateTime.now();
    setState(() {
      _selectedDate = now.add(Duration(days: offsetDays));
    });
  }

  Future<void> _pickDate() async {
    final picked = await showDatePicker(
      context: context,
      initialDate: _selectedDate,
      firstDate: DateTime(2020, 1, 1),
      lastDate: DateTime(2035, 12, 31),
      helpText: 'Selecciona la fecha del movimiento',
    );
    if (picked != null) {
      final now = DateTime.now();
      setState(() {
        _selectedDate = DateTime(
          picked.year,
          picked.month,
          picked.day,
          now.hour,
          now.minute,
          now.second,
        );
      });
    }
  }

  String _formatDateLabel() {
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final target = DateTime(_selectedDate.year, _selectedDate.month, _selectedDate.day);
    final diff = today.difference(target).inDays;
    final suffix = diff == 0 ? ' (Hoy)' : (diff == 1 ? ' (Ayer)' : '');
    return '${DateFormat('dd/MM/yyyy').format(_selectedDate)}$suffix';
  }

  Future<void> _submit() async {
    final raw = _amountController.text.replaceAll(',', '.').trim();
    final val = double.tryParse(raw);
    if (val == null || val <= 0) {
      setState(() {
        _amountError = 'Ingresa un monto mayor a S/ 0.00';
      });
      return;
    }
    if (val > AppConfig.maxTransactionAmount) {
      setState(() {
        _amountError = 'Monto máximo superado';
      });
      return;
    }

    final formattedNote = TransactionModel.formatNoteWithPayment(
      _selectedPayment,
      _noteController.text,
    );

    Navigator.of(context).pop();
    await widget.onSave(
      id: widget.editingTransaction?.id,
      type: _selectedType,
      amount: val,
      category: _selectedCategory,
      note: formattedNote,
      createdAt: _selectedDate,
    );
  }

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final bottomInset = MediaQuery.of(context).viewInsets.bottom;
    final categories = _currentCategories;
    if (!categories.containsKey(_selectedCategory)) {
      _selectedCategory = categories.keys.first;
    }

    return Padding(
      // Empuja suavemente el contenido cuando sube el teclado numérico en Android
      padding: EdgeInsets.only(bottom: bottomInset),
      child: SafeArea(
        top: false,
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 20),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Indicador superior de arrastre
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
                  Text(
                    widget.editingTransaction == null
                        ? 'Registrar Movimiento'
                        : 'Editar Movimiento',
                    style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                  ),
                  IconButton(
                    icon: const Icon(Icons.close_rounded),
                    onPressed: () => Navigator.of(context).pop(),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              SizedBox(
                width: double.infinity,
                child: SegmentedButton<String>(
                  segments: const [
                    ButtonSegment(
                      value: 'gasto',
                      label: Text('Gasto'),
                      icon: Icon(Icons.remove_circle_outline_rounded),
                    ),
                    ButtonSegment(
                      value: 'ingreso',
                      label: Text('Ingreso'),
                      icon: Icon(Icons.add_circle_outline_rounded),
                    ),
                  ],
                  selected: {_selectedType},
                  onSelectionChanged: (selection) {
                    setState(() {
                      _selectedType = selection.first;
                      _selectedCategory = _currentCategories.keys.first;
                    });
                  },
                ),
              ),
              const SizedBox(height: 14),
              TextField(
                controller: _amountController,
                keyboardType: const TextInputType.numberWithOptions(decimal: true),
                style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                decoration: InputDecoration(
                  labelText: 'Monto (${AppConfig.currencySymbol})',
                  prefixText: '${AppConfig.currencySymbol} ',
                  errorText: _amountError,
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(14)),
                  contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                ),
                onSubmitted: (_) => _submit(),
              ),
              const SizedBox(height: 12),
              // Selector de fecha rápido + Calendario
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                decoration: BoxDecoration(
                  color: colorScheme.surfaceContainerHighest.withOpacity(0.55),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(Icons.calendar_month_rounded, size: 18, color: colorScheme.primary),
                        const SizedBox(width: 6),
                        Text(
                          _formatDateLabel(),
                          style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600),
                        ),
                      ],
                    ),
                    Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        TextButton(
                          style: TextButton.styleFrom(
                            visualDensity: VisualDensity.compact,
                            padding: const EdgeInsets.symmetric(horizontal: 8),
                          ),
                          onPressed: () => _setQuickDate(0),
                          child: const Text('Hoy', style: TextStyle(fontSize: 12)),
                        ),
                        TextButton(
                          style: TextButton.styleFrom(
                            visualDensity: VisualDensity.compact,
                            padding: const EdgeInsets.symmetric(horizontal: 8),
                          ),
                          onPressed: () => _setQuickDate(-1),
                          child: const Text('Ayer', style: TextStyle(fontSize: 12)),
                        ),
                        IconButton(
                          visualDensity: VisualDensity.compact,
                          icon: const Icon(Icons.edit_calendar_rounded, size: 18),
                          tooltip: 'Elegir fecha',
                          onPressed: _pickDate,
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 12),
              Text(
                'Categoría:',
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                  color: colorScheme.onSurfaceVariant,
                ),
              ),
              const SizedBox(height: 6),
              Wrap(
                spacing: 6,
                runSpacing: 6,
                children: categories.entries.map((entry) {
                  final isSelected = _selectedCategory == entry.key;
                  final meta = entry.value;
                  return ChoiceChip(
                    avatar: Icon(meta.icon, size: 16, color: meta.color),
                    label: Text(entry.key, style: const TextStyle(fontSize: 12)),
                    selected: isSelected,
                    visualDensity: VisualDensity.compact,
                    onSelected: (_) {
                      setState(() {
                        _selectedCategory = entry.key;
                      });
                    },
                  );
                }).toList(),
              ),
              const SizedBox(height: 12),
              Text(
                'Método / Cuenta:',
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                  color: colorScheme.onSurfaceVariant,
                ),
              ),
              const SizedBox(height: 6),
              Wrap(
                spacing: 6,
                runSpacing: 6,
                children: AppConfig.paymentMethods.map((method) {
                  final isSelected = _selectedPayment == method;
                  return ChoiceChip(
                    label: Text(method, style: const TextStyle(fontSize: 12)),
                    selected: isSelected,
                    visualDensity: VisualDensity.compact,
                    onSelected: (_) {
                      setState(() {
                        _selectedPayment = method;
                      });
                    },
                  );
                }).toList(),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _noteController,
                maxLength: 70,
                decoration: InputDecoration(
                  labelText: 'Nota o detalle (opcional)',
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(14)),
                  contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                ),
                onSubmitted: (_) => _submit(),
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton(
                      onPressed: () => Navigator.of(context).pop(),
                      style: OutlinedButton.styleFrom(
                        minimumSize: const Size.fromHeight(46),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                      ),
                      child: const Text('Cancelar'),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: FilledButton.icon(
                      onPressed: _submit,
                      icon: const Icon(Icons.check_rounded),
                      label: const Text('Guardar'),
                      style: FilledButton.styleFrom(
                        minimumSize: const Size.fromHeight(46),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
