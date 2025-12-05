import json
import os

CONFIG_FILE = '/app/data/bot_config.json' if os.path.exists('/app/data') else 'bot_config.json'

# Default Data (Migrated from utils.py and bot_knowledge.py)
DEFAULT_CONFIG = {
    "signatures": {
        'AI & LLM': [
            'GPTBot', 'ChatGPT', 'ClaudeBot', 'anthropic', 'CCBot', 'Google-Extended', 
            'cohere', 'OAI-SearchBot', 'PerplexityBot', 'Barkrowler', 'Omgilibot', 'FacebookBot'
        ],
        'SEO & Marketing': [
            'AhrefsBot', 'SemrushBot', 'MJ12bot', 'DotBot', 'PetalBot', 'Bytespider', 
            'SerpstatBot', 'DataForSeoBot', 'Screaming Frog', 'SeznamBot', 'hrefsBot', 'ZoominfoBot'
        ],
        'Social Media': [
            'facebookexternalhit', 'Twitterbot', 'LinkedInBot', 'Pinterestbot', 
            'Instagram', 'TikTokBot', 'TelegramBot', 'Discordbot', 'WhatsApp'
        ],
        'Search Engines': [
            'Googlebot', 'Bingbot', 'YandexBot', 'YandexImages', 'Baiduspider', 
            'DuckDuckGo', 'Sogou', 'Exabot', 'Slurp'
        ],
        'Ads': [
            'AdsBot-Google', 'Amazonbot', 'AdIdxbot', 'Applebot'
        ]
    },
    "knowledge_base": {
        'Googlebot': {'description': "Google's primary crawler. Essential for SEO.", 'category': 'Search Engine', 'value_score': 100, 'risk_score': 0, 'verdict': '✅ Essential'},
        'Bingbot': {'description': "Microsoft Bing's crawler.", 'category': 'Search Engine', 'value_score': 95, 'risk_score': 0, 'verdict': '✅ Essential'},
        'YandexBot': {'description': "Yandex search engine crawler.", 'category': 'Search Engine', 'value_score': 90, 'risk_score': 0, 'verdict': '✅ Safe'},
        'GPTBot': {'description': "OpenAI crawler for training models.", 'category': 'AI & LLM', 'value_score': 40, 'risk_score': 2, 'verdict': '⚠️ Neutral'},
        'AhrefsBot': {'description': "SEO tool crawler. Aggressive.", 'category': 'SEO & Marketing', 'value_score': 20, 'risk_score': 4, 'verdict': '📉 Low Value'},
        'MJ12bot': {'description': "Majestic-12 backlink crawler.", 'category': 'SEO & Marketing', 'value_score': 10, 'risk_score': 5, 'verdict': '📉 Low Value'},
        'Bytespider': {'description': "ByteDance/TikTok crawler. Often aggressive.", 'category': 'SEO/AI', 'value_score': 10, 'risk_score': 8, 'verdict': '❌ Aggressive'}
    }
}

class BotManager:
    def __init__(self):
        self.config = self.load_config()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading config, using defaults: {e}")
                return DEFAULT_CONFIG
        return DEFAULT_CONFIG

    def save_config(self):
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(CONFIG_FILE) if os.path.dirname(CONFIG_FILE) else '.', exist_ok=True)
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False

    # --- Signature Methods ---
    def get_signatures(self):
        return self.config.get('signatures', {})

    def add_signature(self, category, signature):
        if category not in self.config['signatures']:
            self.config['signatures'][category] = []
        
        if signature not in self.config['signatures'][category]:
            self.config['signatures'][category].append(signature)
            self.save_config()
            return True
        return False

    # --- Knowledge Base Methods ---
    def get_knowledge_base(self):
        return self.config.get('knowledge_base', {})

    def get_bot_info(self, bot_name):
        kb = self.get_knowledge_base()
        # Try exact match first
        if bot_name in kb:
            return kb[bot_name]
        
        # Try partial match for known bots (simple heuristic)
        for key, info in kb.items():
            if key.lower() in bot_name.lower():
                return info
                
        return {
            'description': "Custom or unknown bot.",
            'category': 'Unknown',
            'value_score': 0,
            'risk_score': 0,
            'verdict': '❓ Unknown'
        }

    def update_bot_info(self, bot_name, description, risk_score, value_score, category):
        kb = self.config['knowledge_base']
        
        verdict = '❓ Unknown'
        if risk_score >= 7: verdict = '❌ Aggressive'
        elif risk_score >= 4: verdict = '📉 Low Value'
        elif value_score >= 80: verdict = '✅ Essential'
        elif value_score >= 50: verdict = '✅ Safe'
        else: verdict = '⚠️ Neutral'

        kb[bot_name] = {
            'description': description,
            'category': category,
            'value_score': value_score,
            'risk_score': risk_score,
            'verdict': verdict
        }
        self.save_config()

    # --- SQL Generators (Moved from utils.py to use dynamic config) ---
    def get_bot_classification_sql(self, column_name='user_agent'):
        signatures = self.get_signatures()
        sql_parts = []
        
        for category, sigs in signatures.items():
            if not sigs: continue
            conditions = [f"position(lower({column_name}), '{sig.lower()}') > 0" for sig in sigs]
            combined_condition = " OR ".join(conditions)
            sql_parts.append(f"WHEN {combined_condition} THEN '{category}'")
        
        return f"""
        CASE 
            { " ".join(sql_parts) }
            ELSE 'Unknown/Human'
        END
        """

    def get_bot_name_sql(self, column_name='user_agent'):
        signatures = self.get_signatures()
        sql_parts = []
        all_sigs = []
        for sigs in signatures.values():
            all_sigs.extend(sigs)
            
        all_sigs.sort(key=len, reverse=True)
        
        for sig in all_sigs:
            sql_parts.append(f"WHEN position(lower({column_name}), '{sig.lower()}') > 0 THEN '{sig}'")
            
        return f"""
        CASE 
            { " ".join(sql_parts) }
            ELSE 'Other'
        END
        """

