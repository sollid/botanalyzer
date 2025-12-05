# Bot Knowledge Base with metadata, descriptions, and scoring

# Score: 0 (Malicious/Spam) to 100 (Critical/Essential)
# Risk: 0 (Safe) to 10 (High Risk)

BOT_KNOWLEDGE_BASE = {
    # --- Search Engines (Essential) ---
    'Googlebot': {
        'description': "Google's primary crawler. Essential for SEO and search ranking.",
        'category': 'Search Engine',
        'value_score': 100,
        'risk_score': 0,
        'verdict': '✅ Essential'
    },
    'Bingbot': {
        'description': "Microsoft Bing's crawler. Important for search visibility.",
        'category': 'Search Engine',
        'value_score': 95,
        'risk_score': 0,
        'verdict': '✅ Essential'
    },
    'YandexBot': {
        'description': "Yandex search engine crawler. Critical for Russian-speaking markets.",
        'category': 'Search Engine',
        'value_score': 90,
        'risk_score': 0,
        'verdict': '✅ Safe'
    },
    'Baiduspider': {
        'description': "Baidu search engine crawler. Critical for Chinese markets.",
        'category': 'Search Engine',
        'value_score': 85,
        'risk_score': 1,
        'verdict': '✅ Safe'
    },
    'DuckDuckGo': {
        'description': "DuckDuckGo privacy-focused search crawler.",
        'category': 'Search Engine',
        'value_score': 80,
        'risk_score': 0,
        'verdict': '✅ Safe'
    },

    # --- AI & LLM (Controversial) ---
    'GPTBot': {
        'description': "OpenAI's crawler used to train GPT models. Respects robots.txt.",
        'category': 'AI & LLM',
        'value_score': 40,
        'risk_score': 2,
        'verdict': '⚠️ Neutral'
    },
    'ChatGPT': {
        'description': "User-triggered requests from ChatGPT (browsing mode).",
        'category': 'AI & LLM',
        'value_score': 50,
        'risk_score': 1,
        'verdict': '✅ Safe'
    },
    'ClaudeBot': {
        'description': "Anthropic's crawler for training Claude models.",
        'category': 'AI & LLM',
        'value_score': 40,
        'risk_score': 2,
        'verdict': '⚠️ Neutral'
    },
    'PerplexityBot': {
        'description': "Perplexity AI search crawler.",
        'category': 'AI & LLM',
        'value_score': 45,
        'risk_score': 2,
        'verdict': '⚠️ Neutral'
    },
    'CCBot': {
        'description': "Common Crawl. Collects massive web datasets used by many AI companies.",
        'category': 'AI & LLM',
        'value_score': 30,
        'risk_score': 3,
        'verdict': '⚠️ Bandwidth Heavy'
    },

    # --- SEO & Marketing (Aggressive) ---
    'AhrefsBot': {
        'description': "SEO tool crawler. Checks backlinks and audits sites. Very aggressive.",
        'category': 'SEO & Marketing',
        'value_score': 20,
        'risk_score': 4,
        'verdict': '📉 Low Value'
    },
    'SemrushBot': {
        'description': "SEMrush SEO tool crawler. Scans for keywords and site health.",
        'category': 'SEO & Marketing',
        'value_score': 20,
        'risk_score': 4,
        'verdict': '📉 Low Value'
    },
    'MJ12bot': {
        'description': "Majestic-12 distributed search engine. Used for SEO backlink research.",
        'category': 'SEO & Marketing',
        'value_score': 10,
        'risk_score': 5,
        'verdict': '📉 Low Value'
    },
    'DotBot': {
        'description': "Moz SEO tool crawler.",
        'category': 'SEO & Marketing',
        'value_score': 15,
        'risk_score': 4,
        'verdict': '📉 Low Value'
    },
    'Bytespider': {
        'description': "ByteDance (TikTok) crawler. Often aggressive and ignores rules.",
        'category': 'SEO/AI',
        'value_score': 10,
        'risk_score': 8,
        'verdict': '❌ Aggressive'
    },
    'PetalBot': {
        'description': "Huawei's search crawler (Aspiegel). High volume, often blocked.",
        'category': 'Search/Mobile',
        'value_score': 30,
        'risk_score': 6,
        'verdict': '⚠️ Caution'
    },

    # --- Social Media ---
    'facebookexternalhit': {
        'description': "Facebook link preview fetcher.",
        'category': 'Social Media',
        'value_score': 70,
        'risk_score': 1,
        'verdict': '✅ Safe'
    },
    'Twitterbot': {
        'description': "X/Twitter link preview fetcher.",
        'category': 'Social Media',
        'value_score': 70,
        'risk_score': 1,
        'verdict': '✅ Safe'
    },

    # --- Ads ---
    'AdsBot-Google': {
        'description': "Checks landing page quality for Google Ads.",
        'category': 'Ads',
        'value_score': 80,
        'risk_score': 0,
        'verdict': '✅ Safe'
    },
    'Amazonbot': {
        'description': "Amazon's crawler for product indexing.",
        'category': 'Ads/Search',
        'value_score': 50,
        'risk_score': 2,
        'verdict': '✅ Safe'
    }
}

def get_bot_info(bot_name):
    return BOT_KNOWLEDGE_BASE.get(bot_name, {
        'description': "Unknown or generic bot.",
        'category': 'Unknown',
        'value_score': 0,
        'risk_score': 0,
        'verdict': '❓ Unknown'
    })

