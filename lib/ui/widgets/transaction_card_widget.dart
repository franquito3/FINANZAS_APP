import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../../config/app_config.dart';
import '../../models/transaction_model.dart';

class TransactionCardWidget extends StatelessWidget {
  final TransactionModel transaction;
  final VoidCallback onEdit;
  final VoidCallback onDelete;

  const TransactionCardWidget({
    super.key,
    required this.transaction,
    required this.onEdit,
    required this.onDelete,
  });

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final meta = AppConfig.getCategoryMeta(transaction.category);
    final fmt = NumberFormat('#,##0.00', 'en_US');
    final dateFmt = DateFormat('dd/MM/yyyy');
    final isExpense = transaction.isExpense;
    final sign = isExpense ? '-' : '+';
    final amountColor = isExpense ? const Color(0xFFF87171) : const Color(0xFF2DD4BF);
    final cleanNote = transaction.cleanNote;
    final method = transaction.paymentMethod;
    final dateStr = dateFmt.format(transaction.createdAt);

    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: colorScheme.surfaceContainerHighest.withOpacity(0.5),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: colorScheme.outlineVariant.withOpacity(0.35)),
      ),
      child: Column(
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(9),
                decoration: BoxDecoration(
                  color: meta.color.withOpacity(0.16),
                  borderRadius: BorderRadius.circular(11),
                ),
                child: Icon(meta.icon, color: meta.color, size: 20),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      transaction.category,
                      style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.bold),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: 2),
                    Text(
                      cleanNote.isNotEmpty ? cleanNote : '$method • $dateStr',
                      style: TextStyle(fontSize: 11.5, color: colorScheme.onSurfaceVariant),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              Text(
                '$sign ${AppConfig.currencySymbol} ${fmt.format(transaction.amount)}',
                style: TextStyle(
                  fontSize: 14.5,
                  fontWeight: FontWeight.w800,
                  color: amountColor,
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Expanded(
                child: Row(
                  children: [
                    Icon(
                      transaction.synced ? Icons.cloud_done_rounded : Icons.cloud_off_rounded,
                      size: 13,
                      color: transaction.synced
                          ? const Color(0xFF2DD4BF)
                          : colorScheme.onSurfaceVariant,
                    ),
                    const SizedBox(width: 5),
                    Flexible(
                      child: Text(
                        '$dateStr • $method',
                        style: TextStyle(fontSize: 11, color: colorScheme.onSurfaceVariant),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
              ),
              Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  IconButton(
                    visualDensity: VisualDensity.compact,
                    constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
                    padding: EdgeInsets.zero,
                    icon: const Icon(Icons.edit_outlined, size: 17),
                    tooltip: 'Editar',
                    onPressed: onEdit,
                  ),
                  IconButton(
                    visualDensity: VisualDensity.compact,
                    constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
                    padding: EdgeInsets.zero,
                    icon: const Icon(Icons.delete_outline_rounded, size: 17, color: Color(0xFFF87171)),
                    tooltip: 'Eliminar',
                    onPressed: onDelete,
                  ),
                ],
              ),
            ],
          ),
        ],
      ),
    );
  }
}
