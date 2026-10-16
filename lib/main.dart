import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:intl/date_symbol_data_local.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'config/app_config.dart';
import 'services/local_storage_service.dart';
import 'services/supabase_sync_service.dart';
import 'ui/screens/home_screen.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await initializeDateFormatting('es_ES', null);

  await Supabase.initialize(
    url: AppConfig.supabaseUrl,
    anonKey: AppConfig.supabaseAnonKey,
    authOptions: const FlutterAuthClientOptions(
      authFlowType: AuthFlowType.pkce,
    ),
  );

  final prefs = await SharedPreferences.getInstance();
  final localStorage = LocalStorageService(prefs);
  final supabaseService = SupabaseSyncService(localStorage);

  runApp(
    MisFinanzasApp(
      localStorage: localStorage,
      supabaseService: supabaseService,
    ),
  );
}

class MisFinanzasApp extends StatefulWidget {
  final LocalStorageService localStorage;
  final SupabaseSyncService supabaseService;

  const MisFinanzasApp({
    super.key,
    required this.localStorage,
    required this.supabaseService,
  });

  @override
  State<MisFinanzasApp> createState() => _MisFinanzasAppState();
}

class _MisFinanzasAppState extends State<MisFinanzasApp> {
  late bool _isDarkMode;

  @override
  void initState() {
    super.initState();
    _isDarkMode = widget.localStorage.isDarkMode;
  }

  void _toggleTheme() {
    setState(() {
      _isDarkMode = !_isDarkMode;
    });
    widget.localStorage.setDarkMode(_isDarkMode);
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Mis Finanzas',
      debugShowCheckedModeBanner: false,
      themeMode: _isDarkMode ? ThemeMode.dark : ThemeMode.light,
      localizationsDelegates: const [
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      supportedLocales: const [
        Locale('es', 'ES'),
        Locale('en', 'US'),
      ],
      theme: ThemeData(
        useMaterial3: true,
        colorSchemeSeed: AppConfig.seedColor,
        brightness: Brightness.light,
      ),
      darkTheme: ThemeData(
        useMaterial3: true,
        colorSchemeSeed: AppConfig.seedColor,
        brightness: Brightness.dark,
      ),
      home: HomeScreen(
        localStorage: widget.localStorage,
        supabaseService: widget.supabaseService,
        onToggleTheme: _toggleTheme,
        isDarkMode: _isDarkMode,
      ),
    );
  }
}
