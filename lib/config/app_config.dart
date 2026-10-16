import 'package:flutter/material.dart';

class CategoryMeta {
  final String name;
  final IconData icon;
  final Color color;
  final String group;

  const CategoryMeta({
    required this.name,
    required this.icon,
    required this.color,
    this.group = 'Ingreso',
  });
}

class AppConfig {
  static const String supabaseUrl = 'https://gwfbmplmszezjunpvllz.supabase.co';
  static const String supabaseAnonKey = 'sb_publishable_Mmd4WFqPDyzeT5wW-ww2Sg_ICMOLOR4';
  static const String oauthRedirectUrl = 'misfinanzas://login-callback';
  static const String currencySymbol = 'S/';
  static const double maxTransactionAmount = 9999999.99;
  static const Color seedColor = Color(0xFF10B981);

  static const Map<String, CategoryMeta> expenseCategories = {
    'Alimentación': CategoryMeta(
      name: 'Alimentación',
      icon: Icons.restaurant_rounded,
      color: Color(0xFFFB923C),
      group: 'Necesidades (50%)',
    ),
    'Vivienda y Servicios': CategoryMeta(
      name: 'Vivienda y Servicios',
      icon: Icons.home_rounded,
      color: Color(0xFF60A5FA),
      group: 'Necesidades (50%)',
    ),
    'Transporte': CategoryMeta(
      name: 'Transporte',
      icon: Icons.directions_car_rounded,
      color: Color(0xFF22D3EE),
      group: 'Necesidades (50%)',
    ),
    'Salud y Farmacia': CategoryMeta(
      name: 'Salud y Farmacia',
      icon: Icons.medical_services_rounded,
      color: Color(0xFFF87171),
      group: 'Necesidades (50%)',
    ),
    'Educación': CategoryMeta(
      name: 'Educación',
      icon: Icons.school_rounded,
      color: Color(0xFF818CF8),
      group: 'Necesidades (50%)',
    ),
    'Ocio y Salidas': CategoryMeta(
      name: 'Ocio y Salidas',
      icon: Icons.local_cafe_rounded,
      color: Color(0xFFC084FC),
      group: 'Deseos (30%)',
    ),
    'Compras Personales': CategoryMeta(
      name: 'Compras Personales',
      icon: Icons.shopping_bag_rounded,
      color: Color(0xFFF472B6),
      group: 'Deseos (30%)',
    ),
    'Suscripciones': CategoryMeta(
      name: 'Suscripciones',
      icon: Icons.smart_display_rounded,
      color: Color(0xFFFB7185),
      group: 'Deseos (30%)',
    ),
    'Ahorro e Inversión': CategoryMeta(
      name: 'Ahorro e Inversión',
      icon: Icons.savings_rounded,
      color: Color(0xFF4ADE80),
      group: 'Futuro (20%)',
    ),
    'Deudas y Préstamos': CategoryMeta(
      name: 'Deudas y Préstamos',
      icon: Icons.credit_score_rounded,
      color: Color(0xFFFBBF24),
      group: 'Futuro (20%)',
    ),
  };

  static const Map<String, CategoryMeta> incomeCategories = {
    'Sueldo / Honorarios': CategoryMeta(
      name: 'Sueldo / Honorarios',
      icon: Icons.account_balance_wallet_rounded,
      color: Color(0xFF2DD4BF),
    ),
    'Negocio / Ventas': CategoryMeta(
      name: 'Negocio / Ventas',
      icon: Icons.storefront_rounded,
      color: Color(0xFF10B981),
    ),
    'Inversiones / Intereses': CategoryMeta(
      name: 'Inversiones / Intereses',
      icon: Icons.trending_up_rounded,
      color: Color(0xFF84CC16),
    ),
    'Otros Ingresos': CategoryMeta(
      name: 'Otros Ingresos',
      icon: Icons.payments_rounded,
      color: Color(0xFF38BDF8),
    ),
  };

  static const List<String> paymentMethods = [
    'Efectivo',
    'Yape / Plin',
    'Tarjeta Débito',
    'Tarjeta Crédito',
    'Transferencia',
  ];

  static const Map<int, String> shortMonthNames = {
    1: 'Ene',
    2: 'Feb',
    3: 'Mar',
    4: 'Abr',
    5: 'May',
    6: 'Jun',
    7: 'Jul',
    8: 'Ago',
    9: 'Sep',
    10: 'Oct',
    11: 'Nov',
    12: 'Dic',
  };

  static const Map<int, String> fullMonthNames = {
    1: 'Enero',
    2: 'Febrero',
    3: 'Marzo',
    4: 'Abril',
    5: 'Mayo',
    6: 'Junio',
    7: 'Julio',
    8: 'Agosto',
    9: 'Septiembre',
    10: 'Octubre',
    11: 'Noviembre',
    12: 'Diciembre',
  };

  static CategoryMeta getCategoryMeta(String category) {
    return expenseCategories[category] ??
        incomeCategories[category] ??
        CategoryMeta(
          name: category,
          icon: Icons.receipt_long_rounded,
          color: Colors.blueGrey,
          group: 'Deseos (30%)',
        );
  }
}
