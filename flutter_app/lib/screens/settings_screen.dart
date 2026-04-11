import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../config/api_config.dart';
import '../providers/settings_provider.dart';
import '../services/api_service.dart';
import '../utils/constants.dart';
import '../utils/validators.dart';
import '../widgets/custom_app_bar.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  late final TextEditingController _urlController;
  bool _testingApi = false;
  String? _apiStatus;

  @override
  void initState() {
    super.initState();
    final settings = context.read<SettingsProvider>();
    _urlController = TextEditingController(text: settings.baseUrl);
  }

  @override
  void dispose() {
    _urlController.dispose();
    super.dispose();
  }

  Future<void> _testApiConnection() async {
    final url = _urlController.text.trim();
    final error = Validators.apiUrl(url);
    if (error != null) {
      setState(() => _apiStatus = error);
      return;
    }

    setState(() {
      _testingApi = true;
      _apiStatus = null;
    });

    try {
      final api = ApiService(baseUrl: url);
      final healthy = await api.checkHealth();
      setState(() {
        _apiStatus = healthy ? '✓ Connected successfully' : '✗ API not healthy';
      });
    } catch (e) {
      setState(() => _apiStatus = '✗ Connection failed: ${e.toString()}');
    } finally {
      setState(() => _testingApi = false);
    }
  }

  Future<void> _saveApiUrl() async {
    final url = _urlController.text.trim();
    final error = Validators.apiUrl(url);
    if (error != null) {
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text(error)));
      return;
    }
    await context.read<SettingsProvider>().setBaseUrl(url);
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('API URL saved')));
    }
  }

  @override
  Widget build(BuildContext context) {
    final settings = context.watch<SettingsProvider>();
    final theme = Theme.of(context);

    return Scaffold(
      appBar: const CustomAppBar(title: 'Settings', showBackButton: false),
      body: ListView(
        children: [
          // ── API Configuration ──
          _SectionHeader('API Configuration'),
          Padding(
            padding: const EdgeInsets.symmetric(
                horizontal: AppConstants.spaceMd),
            child: Column(
              children: [
                TextFormField(
                  controller: _urlController,
                  decoration: InputDecoration(
                    labelText: 'Backend URL',
                    hintText: ApiConfig.defaultBaseUrl,
                    prefixIcon: const Icon(Icons.link_outlined),
                    suffixIcon: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        if (_testingApi)
                          const Padding(
                            padding: EdgeInsets.all(12),
                            child: SizedBox(
                                width: 18,
                                height: 18,
                                child: CircularProgressIndicator(
                                    strokeWidth: 2)),
                          )
                        else
                          IconButton(
                            onPressed: _testApiConnection,
                            icon: const Icon(Icons.network_check_outlined),
                            tooltip: 'Test connection',
                          ),
                      ],
                    ),
                  ),
                  keyboardType: TextInputType.url,
                  textInputAction: TextInputAction.done,
                  onFieldSubmitted: (_) => _saveApiUrl(),
                ),
                if (_apiStatus != null)
                  Padding(
                    padding:
                        const EdgeInsets.only(top: AppConstants.spaceSm),
                    child: Text(
                      _apiStatus!,
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: _apiStatus!.startsWith('✓')
                            ? AppConstants.colorSafe
                            : AppConstants.colorFraud,
                      ),
                    ),
                  ),
                const SizedBox(height: AppConstants.spaceSm),
                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton(
                        onPressed: _testApiConnection,
                        child: const Text('Test Connection'),
                      ),
                    ),
                    const SizedBox(width: AppConstants.spaceSm),
                    Expanded(
                      child: ElevatedButton(
                        onPressed: _saveApiUrl,
                        child: const Text('Save URL'),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: AppConstants.spaceMd),

          // ── Appearance ──
          _SectionHeader('Appearance'),
          ListTile(
            leading: const Icon(Icons.palette_outlined),
            title: const Text('Theme'),
            subtitle: Text(_themeLabel(settings.themeMode)),
            trailing: DropdownButton<ThemeMode>(
              value: settings.themeMode,
              underline: const SizedBox.shrink(),
              onChanged: (m) {
                if (m != null) settings.setThemeMode(m);
              },
              items: const [
                DropdownMenuItem(
                  value: ThemeMode.system,
                  child: Text('System'),
                ),
                DropdownMenuItem(
                  value: ThemeMode.light,
                  child: Text('Light'),
                ),
                DropdownMenuItem(
                  value: ThemeMode.dark,
                  child: Text('Dark'),
                ),
              ],
            ),
          ),

          // ── Notifications ──
          _SectionHeader('Notifications'),
          SwitchListTile(
            secondary: const Icon(Icons.notifications_outlined),
            title: const Text('Push Notifications'),
            subtitle: const Text('Get alerts for high-risk transactions'),
            value: settings.notificationsEnabled,
            onChanged: settings.setNotificationsEnabled,
          ),

          // ── Sync ──
          _SectionHeader('Sync'),
          SwitchListTile(
            secondary: const Icon(Icons.sync_outlined),
            title: const Text('Auto-sync'),
            subtitle: const Text('Sync transaction history with server'),
            value: settings.autoSyncEnabled,
            onChanged: settings.setAutoSyncEnabled,
          ),
          if (settings.lastSyncTime != null)
            ListTile(
              leading: const Icon(Icons.history_outlined),
              title: const Text('Last sync'),
              subtitle: Text(settings.lastSyncTime!.toLocal().toString()),
            ),

          // ── About ──
          _SectionHeader('About'),
          ListTile(
            leading: const Icon(Icons.info_outline),
            title: const Text('App Version'),
            subtitle: Text(
                '${AppConstants.appVersion} (Build ${AppConstants.appBuildNumber})'),
          ),
          ListTile(
            leading: const Icon(Icons.security_outlined),
            title: const Text('Privacy Policy'),
            trailing: const Icon(Icons.chevron_right),
            onTap: () {},
          ),
          ListTile(
            leading: const Icon(Icons.description_outlined),
            title: const Text('Open Source Licenses'),
            trailing: const Icon(Icons.chevron_right),
            onTap: () => showLicensePage(context: context),
          ),
          const SizedBox(height: AppConstants.spaceXl),
        ],
      ),
    );
  }

  String _themeLabel(ThemeMode mode) {
    switch (mode) {
      case ThemeMode.light:
        return 'Light';
      case ThemeMode.dark:
        return 'Dark';
      case ThemeMode.system:
        return 'System default';
    }
  }
}

class _SectionHeader extends StatelessWidget {
  final String title;

  const _SectionHeader(this.title);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(
          AppConstants.spaceMd, AppConstants.spaceLg,
          AppConstants.spaceMd, AppConstants.spaceSm),
      child: Text(
        title.toUpperCase(),
        style: Theme.of(context).textTheme.labelSmall?.copyWith(
              color: Theme.of(context).colorScheme.primary,
              fontWeight: FontWeight.bold,
              letterSpacing: 1.5,
            ),
      ),
    );
  }
}
