import socket

def verify_googlebot_ip(ip_address):
    """
    Verifies if an IP address belongs to Googlebot via Reverse DNS.
    Returns: (bool, str) -> (is_verified, hostname_or_status)
    """
    try:
        # 1. Reverse DNS lookup
        hostname, _, _ = socket.gethostbyaddr(ip_address)
        
        # 2. Check domain suffix
        if not (hostname.endswith('.googlebot.com') or hostname.endswith('.google.com')):
            return False, hostname

        # 3. Forward DNS lookup to verify
        _, _, ip_list = socket.gethostbyname_ex(hostname)
        
        if ip_address in ip_list:
            return True, hostname
        else:
            return False, f"Fake: {hostname}"
            
    except Exception as e:
        return False, "Lookup Failed"

def generate_regex_sql(patterns_dict):
    """
    Generates a SQL CASE WHEN statement for grouping URLs by regex patterns.
    patterns_dict: { 'Group Name': 'regex_pattern', ... }
    """
    if not patterns_dict:
        return "'Other'"
        
    sql_parts = []
    for group, pattern in patterns_dict.items():
        # Escape single quotes in pattern just in case
        safe_pattern = pattern.replace("'", "''")
        sql_parts.append(f"WHEN match(url, '{safe_pattern}') THEN '{group}'")
        
    return f"CASE {' '.join(sql_parts)} ELSE 'Other' END"

# --- Bot Classification Definitions ---

BOT_SIGNATURES = {
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
}

def get_bot_classification_sql(column_name='user_agent'):
    """
    Generates a SQL CASE WHEN statement to classify bots based on User-Agent.
    """
    sql_parts = []
    
    # Priority: AI > SEO > Social > Ads > Search
    # This order matters because some UAs might contain multiple keywords (e.g. Googlebot)
    
    for category, signatures in BOT_SIGNATURES.items():
        conditions = [f"position(lower({column_name}), '{sig.lower()}') > 0" for sig in signatures]
        combined_condition = " OR ".join(conditions)
        sql_parts.append(f"WHEN {combined_condition} THEN '{category}'")
    
    return f"""
    CASE 
        { " ".join(sql_parts) }
        ELSE 'Unknown/Human'
    END
    """

def get_bot_name_sql(column_name='user_agent'):
    """
    Generates a massive SQL CASE WHEN to extract the specific bot name.
    """
    sql_parts = []
    all_sigs = []
    for sigs in BOT_SIGNATURES.values():
        all_sigs.extend(sigs)
        
    # Sort by length desc to match longer specific names first (e.g. "AdsBot-Google" before "Google")
    all_sigs.sort(key=len, reverse=True)
    
    for sig in all_sigs:
        sql_parts.append(f"WHEN position(lower({column_name}), '{sig.lower()}') > 0 THEN '{sig}'")
        
    return f"""
    CASE 
        { " ".join(sql_parts) }
        ELSE 'Other'
    END
    """
