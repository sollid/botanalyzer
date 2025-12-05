import streamlit as st
import pandas as pd
import plotly.express as px
from db import get_client
from utils import verify_googlebot_ip, generate_regex_sql
from bot_manager import BotManager
from datetime import datetime, timedelta

st.set_page_config(page_title="BotAnalyzer Pro", layout="wide", page_icon="🛡️")

# --- Init Bot Manager ---
bot_manager = BotManager()

# Assign manager methods to variables for compatibility with existing code structure if needed,
# or use bot_manager directly.
# Updating globals that were previously imported
BOT_SIGNATURES = bot_manager.get_signatures()
get_bot_classification_sql = bot_manager.get_bot_classification_sql
get_bot_name_sql = bot_manager.get_bot_name_sql
get_bot_info = bot_manager.get_bot_info

# --- Session State Init ---
if 'pagination_offset' not in st.session_state:
    st.session_state.pagination_offset = 0

# --- Database Connection ---
def get_db_client():
    try:
        return get_client()
    except Exception as e:
        st.error(f"Could not connect to database: {e}")
        return None

client = get_db_client()

if not client:
    st.stop()

# --- Helper Functions ---
@st.cache_data(ttl=600)
def run_query(query):
    """Executes SQL query with caching."""
    try:
        return client.query_df(query)
    except Exception as e:
        st.error(f"Query failed: {e}")
        return pd.DataFrame()

def download_csv(df, filename="data.csv"):
    return st.download_button(
        label="📥 Download CSV",
        data=df.to_csv(index=False).encode('utf-8'),
        file_name=filename,
        mime='text/csv',
    )

# --- Sidebar & Global Filters ---
st.sidebar.title("🛡️ BotAnalyzer")

page = st.sidebar.radio(
    "Navigate", 
    ["Dashboard", "Security & Anomalies", "SEO & Crawl Budget", "Bot Encyclopedia", "Log Explorer"]
)

st.sidebar.markdown("---")
st.sidebar.subheader("📅 Date Filter")

# Default to last 7 days
default_start = datetime.now() - timedelta(days=7)
default_end = datetime.now()

date_range = st.sidebar.date_input(
    "Select Range",
    (default_start, default_end),
    max_value=datetime.now()
)

if len(date_range) == 2:
    start_date, end_date = date_range
    # Format for ClickHouse: 'YYYY-MM-DD HH:MM:SS'
    start_str = start_date.strftime('%Y-%m-%d 00:00:00')
    end_str = end_date.strftime('%Y-%m-%d 23:59:59')
    
    date_filter = f"timestamp BETWEEN '{start_str}' AND '{end_str}'"
else:
    st.sidebar.warning("Select a date range")
    st.stop()

# --- Dashboard ---
if page == "Dashboard":
    st.title("📊 General Overview")
    
    # KPIs
    kpi_query = f"""
    SELECT 
        count() as total_requests,
        uniq(client_ip) as unique_ips,
        sum(response_size) / 1024 / 1024 as bandwidth_mb,
        countIf(status_code >= 400) / count() * 100 as error_rate
    FROM access_logs
    WHERE {date_filter}
    """
    df_kpi = run_query(kpi_query)
    
    if not df_kpi.empty:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Requests", f"{df_kpi['total_requests'][0]:,}")
        col2.metric("Unique IPs", f"{df_kpi['unique_ips'][0]:,}")
        col3.metric("Bandwidth (MB)", f"{df_kpi['bandwidth_mb'][0]:.2f}")
        col4.metric("Error Rate", f"{df_kpi['error_rate'][0]:.2f}%")
    
    # Time Series
    st.subheader("Traffic Over Time")
    trend_query = f"""
    SELECT 
        toStartOfHour(timestamp) as time,
        count() as requests,
        countIf(status_code >= 400) as errors
    FROM access_logs
    WHERE {date_filter}
    GROUP BY time
    ORDER BY time
    """
    df_trend = run_query(trend_query)
    if not df_trend.empty:
        fig = px.line(df_trend, x='time', y=['requests', 'errors'], title="Requests vs Errors (Hourly)")
        st.plotly_chart(fig, use_container_width=True)

# --- Security & Anomalies ---
elif page == "Security & Anomalies":
    st.title("🔒 Security & Anomalies")
    
    tab1, tab2, tab3, tab4 = st.tabs(["Rate Limiting (RPS)", "404 Attacks", "Bot Traffic Explorer", "Bot Volume Analysis"])
    
    with tab1:
        st.subheader("🚨 High RPS Detection")
        st.markdown("IPs with abnormal request rates in short bursts.")
        
        rps_threshold = st.slider("Min Requests per Minute", 10, 500, 60)
        
        rps_query = f"""
        SELECT 
            client_ip, 
            country,
            toStartOfMinute(timestamp) as minute,
            count() as requests_per_min,
            any(user_agent) as sample_ua
        FROM access_logs
        WHERE {date_filter}
        GROUP BY client_ip, country, minute
        HAVING requests_per_min > {rps_threshold}
        ORDER BY requests_per_min DESC
        LIMIT 50
        """
        df_rps = run_query(rps_query)
        st.dataframe(df_rps, use_container_width=True)
        download_csv(df_rps, "high_rps_ips.csv")

    with tab2:
        st.subheader("🔍 404 Attack Detector")
        st.markdown("IPs generating high volumes of 404 errors (Scanning/Fuzzing).")
        
        scan_query = f"""
        SELECT 
            client_ip,
            country,
            count() as total_404s,
            count(DISTINCT url) as unique_urls_probed
        FROM access_logs
        WHERE {date_filter} AND status_code = 404
        GROUP BY client_ip, country
        ORDER BY total_404s DESC
        LIMIT 50
        """
        df_scan = run_query(scan_query)
        st.dataframe(df_scan, use_container_width=True)
        download_csv(df_scan, "404_scanners.csv")
        
    with tab3:
        st.subheader("🤖 Bot Traffic Explorer")
        st.markdown("Analyze traffic by Bot Category with dynamic grouping.")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Filter by Category
            categories = list(BOT_SIGNATURES.keys())
            selected_categories = st.multiselect("1. Filter by Bot Category", categories, default=categories)
            
            # Additional Filters
            st.markdown("### Additional Filters")
            min_requests = st.number_input("Min Requests", min_value=1, value=1, step=10)
            search_query = st.text_input("Search (Name, IP, UA)")
            
        with col2:
            # Dynamic Grouping
            dimension_map = {
                'Bot Name': {'sql': get_bot_name_sql('user_agent'), 'col': 'bot_name'},
                'Bot Category': {'sql': get_bot_classification_sql('user_agent'), 'col': 'bot_category'},
                'IP Address': {'sql': 'client_ip', 'col': 'client_ip'},
                'User Agent': {'sql': 'user_agent', 'col': 'user_agent'},
                'Country': {'sql': 'country', 'col': 'country'},
                'URL': {'sql': 'url', 'col': 'url'},
                'Method': {'sql': 'method', 'col': 'method'},
                'Status Code': {'sql': 'toString(status_code)', 'col': 'status_code_str'}
            }
            
            default_dims = ['Bot Category', 'Bot Name', 'IP Address', 'Country']
            selected_dims = st.multiselect("2. Select Columns (Group By)", list(dimension_map.keys()), default=default_dims)

        if selected_categories and selected_dims:
            # Generate SQL parts
            select_clauses = []
            group_clauses = []
            
            for dim in selected_dims:
                sql_expr = dimension_map[dim]['sql']
                alias = dimension_map[dim]['col']
                select_clauses.append(f"{sql_expr} as {alias}")
                group_clauses.append(alias)
            
            # Filters Logic
            cat_sql = get_bot_classification_sql('user_agent')
            
            having_conditions = []
            
            # 1. Category Filter
            if len(selected_categories) == 1:
                having_conditions.append(f"({cat_sql}) = '{selected_categories[0]}'")
            else:
                having_conditions.append(f"({cat_sql}) IN {tuple(selected_categories)}")
            
            # 2. Min Requests Filter
            having_conditions.append(f"count() >= {min_requests}")
            
            # 3. Search Filter (Applied to result columns if they exist, or raw columns)
            if search_query:
                name_sql = get_bot_name_sql('user_agent')
                search_conds = [
                    f"client_ip ILIKE '%{search_query}%'",
                    f"user_agent ILIKE '%{search_query}%'",
                    f"({name_sql}) ILIKE '%{search_query}%'"
                ]
                having_conditions.append(f"({' OR '.join(search_conds)})")
                
            having_sql = " AND ".join(having_conditions)
            
            bot_explorer_query = f"""
            SELECT 
                {', '.join(select_clauses)},
                count() as requests,
                countIf(status_code >= 400) as errors,
                round(countIf(status_code >= 400) / count() * 100, 2) as error_rate
            FROM access_logs
            WHERE {date_filter} 
            GROUP BY {', '.join(group_clauses)}
            HAVING {having_sql}
            ORDER BY requests DESC
            LIMIT 1000
            """
            
            df_bots = run_query(bot_explorer_query)
            st.dataframe(df_bots, use_container_width=True)
            download_csv(df_bots, "custom_bot_report.csv")
            
            # Visualization based on primary group
            if not df_bots.empty and len(selected_dims) > 0:
                primary_col = dimension_map[selected_dims[0]]['col']
                if len(df_bots) > 0:
                    st.caption(f"Top 10 by {selected_dims[0]}")
                    chart_data = df_bots.head(10)
                    fig_bar = px.bar(chart_data, x=primary_col, y='requests', color='errors', title=f"Traffic by {selected_dims[0]}")
                    st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("Please select at least one category and one column to group by.")

    with tab4:
        st.subheader("📈 Bot Volume Analysis (Time Series)")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            # Optional filter for specific bots in the chart
            specific_bot_filter = st.text_input("Filter Chart by Bot Name (e.g. GPTBot)")
        
        # Aggregated Volume by Category over Time
        cat_sql = get_bot_classification_sql('user_agent')
        name_sql = get_bot_name_sql('user_agent')
        
        # Base conditions
        chart_having = ["bot_category != 'Unknown/Human'"]
        if specific_bot_filter:
            chart_having.append(f"bot_name ILIKE '%{specific_bot_filter}%'")
        
        volume_query = f"""
        SELECT 
            toStartOfHour(timestamp) as time,
            {cat_sql} as bot_category,
            {name_sql} as bot_name,
            count() as requests
        FROM access_logs
        WHERE {date_filter}
        GROUP BY time, bot_category, bot_name
        HAVING {" AND ".join(chart_having)}
        ORDER BY time
        """
        
        df_vol = run_query(volume_query)
        
        if not df_vol.empty:
            # If filtered by specific bot, color by Bot Name, otherwise by Category
            color_col = 'bot_name' if specific_bot_filter else 'bot_category'
            
            # Aggregate locally if we are showing categories (sum up bots in same category)
            if not specific_bot_filter:
                df_chart = df_vol.groupby(['time', 'bot_category'])['requests'].sum().reset_index()
                fig_vol = px.area(df_chart, x='time', y='requests', color='bot_category', title="Bot Traffic Volume over Time")
            else:
                fig_vol = px.area(df_vol, x='time', y='requests', color='bot_name', title=f"Volume for bots matching '{specific_bot_filter}'")
                
            st.plotly_chart(fig_vol, use_container_width=True)
            
            # Top specific bots
            st.subheader("Top Specific Bots by Volume")
            name_sql = get_bot_name_sql('user_agent')
            top_bots_query = f"""
            SELECT 
                {name_sql} as bot_name,
                count() as requests,
                countIf(status_code >= 400) as errors,
                round(countIf(status_code >= 400) / count() * 100, 2) as error_rate_pct
            FROM access_logs
            WHERE {date_filter}
            GROUP BY bot_name
            HAVING bot_name != 'Other'
            ORDER BY requests DESC
            """
            df_top_bots = run_query(top_bots_query)
            
            col1, col2 = st.columns([2, 1])
            with col1:
                st.bar_chart(df_top_bots.head(20).set_index('bot_name')['requests'])
            with col2:
                st.dataframe(df_top_bots, use_container_width=True, height=400)
                download_csv(df_top_bots, "top_bots_volume.csv")

# --- SEO & Crawl Budget ---
elif page == "SEO & Crawl Budget":
    st.title("🕷️ SEO & Crawl Budget")
    
    tab1, tab2 = st.tabs(["Googlebot Analysis", "Crawl Budget Grouping"])
    
    with tab1:
        st.subheader("Googlebot Activity")
        
        # Googlebot stats
        gb_stats_query = f"""
        SELECT 
            count() as total_hits,
            countIf(status_code = 200) as ok_200,
            countIf(status_code = 404) as err_404,
            countIf(status_code >= 500) as err_500
        FROM access_logs
        WHERE {date_filter} AND user_agent ILIKE '%Googlebot%'
        """
        df_gb_stats = run_query(gb_stats_query)
        if not df_gb_stats.empty:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total Googlebot Hits", f"{df_gb_stats['total_hits'][0]:,}")
            c2.metric("200 OK", f"{df_gb_stats['ok_200'][0]:,}")
            c3.metric("404 Errors", f"{df_gb_stats['err_404'][0]:,}")
            c4.metric("5xx Errors", f"{df_gb_stats['err_500'][0]:,}")
        
        st.subheader("Verify Googlebot IPs")
        st.info("⚠️ Verification performs real-time DNS lookups. Use on small subsets.")
        
        gb_ip_query = f"""
        SELECT client_ip, count() as requests
        FROM access_logs
        WHERE {date_filter} AND user_agent ILIKE '%Googlebot%'
        GROUP BY client_ip
        ORDER BY requests DESC
        LIMIT 20
        """
        df_gb_ips = run_query(gb_ip_query)
        
        if not df_gb_ips.empty:
            if st.button("Verify Top 20 IPs"):
                results = []
                progress_bar = st.progress(0)
                for i, row in df_gb_ips.iterrows():
                    ip = row['client_ip']
                    is_valid, hostname = verify_googlebot_ip(ip)
                    results.append({'IP': ip, 'Requests': row['requests'], 'Verified': is_valid, 'Hostname': hostname})
                    progress_bar.progress((i + 1) / len(df_gb_ips))
                
                st.dataframe(pd.DataFrame(results), use_container_width=True)
            else:
                st.dataframe(df_gb_ips, use_container_width=True)

    with tab2:
        st.subheader("Crawl Distribution by Page Type")
        
        default_patterns = """Product: /product/*
Category: /category/*
Blog: /blog/*
API: /api/*"""
        
        patterns_input = st.text_area("Define URL Patterns (Name: Pattern)", value=default_patterns, height=150)
        
        if patterns_input:
            patterns = {}
            for line in patterns_input.split('\n'):
                if ':' in line:
                    name, pat = line.split(':', 1)
                    patterns[name.strip()] = pat.strip()
            
            case_sql = generate_regex_sql(patterns)
            
            group_query = f"""
            SELECT 
                {case_sql} as page_group,
                count() as requests
            FROM access_logs
            WHERE {date_filter}
            GROUP BY page_group
            ORDER BY requests DESC
            """
            df_group = run_query(group_query)
            
            if not df_group.empty:
                fig_pie = px.pie(df_group, values='requests', names='page_group', title="Crawl Budget Distribution")
                st.plotly_chart(fig_pie, use_container_width=True)
                download_csv(df_group, "crawl_budget_groups.csv")

# --- Bot Encyclopedia ---
elif page == "Bot Encyclopedia":
    st.title("📚 Bot Encyclopedia")
    st.markdown("Detailed information about known bots and their observed activity on your site.")
    
    # Tabs for Viewing and Editing
    tab_view, tab_edit = st.tabs(["View Encyclopedia", "Manage Bots"])
    
    with tab_view:
        # 1. Get observed bots stats
        name_sql = get_bot_name_sql('user_agent')
        stats_query = f"""
        SELECT 
            {name_sql} as bot_name,
            count() as total_requests,
            uniq(client_ip) as unique_ips,
            max(timestamp) as last_seen,
            countIf(status_code >= 400) as errors
        FROM access_logs
        GROUP BY bot_name
        HAVING bot_name != 'Other'
        ORDER BY total_requests DESC
        """
        df_stats = run_query(stats_query)
        
        # 2. Merge with Knowledge Base (from Manager)
        bot_data = []
        
        # Create a set of observed bots for quick lookup
        observed_bots = {}
        if not df_stats.empty:
            observed_bots = df_stats.set_index('bot_name').to_dict('index')
        
        # Combine Knowledge Base + Observed
        kb = bot_manager.get_knowledge_base()
        all_bot_names = set(kb.keys()) | set(observed_bots.keys())
        
        for name in all_bot_names:
            info = bot_manager.get_bot_info(name)
            stats = observed_bots.get(name, {
                'total_requests': 0, 
                'unique_ips': 0, 
                'last_seen': None,
                'errors': 0
            })
            
            # Calculate Risk Badge
            risk_score = info.get('risk_score', 0)
            if risk_score >= 7:
                risk_label = "🔴 High Risk"
            elif risk_score >= 4:
                risk_label = "🟠 Medium Risk"
            else:
                risk_label = "🟢 Low Risk"
                
            bot_data.append({
                'Bot Name': name,
                'Category': info.get('category', 'Unknown'),
                'Verdict': info.get('verdict', '❓ Unknown'),
                'Risk Level': risk_label,
                'Description': info.get('description', 'No description'),
                'Observed Requests': stats['total_requests'],
                'Unique IPs': stats['unique_ips'],
                'Last Seen': stats['last_seen'],
                'Errors': stats['errors']
            })
            
        df_encyclopedia = pd.DataFrame(bot_data)
        
        # Filters
        col1, col2 = st.columns([2, 1])
        with col1:
            search_bot = st.text_input("Search Encyclopedia", placeholder="Google, GPT, Ahrefs...")
        with col2:
            sort_by = st.selectbox("Sort By", ["Observed Requests", "Risk Level", "Bot Name"], index=0)
            
        # Apply Filters
        if search_bot:
            df_encyclopedia = df_encyclopedia[
                df_encyclopedia['Bot Name'].str.contains(search_bot, case=False) | 
                df_encyclopedia['Description'].str.contains(search_bot, case=False)
            ]
            
        if sort_by == "Observed Requests":
            df_encyclopedia = df_encyclopedia.sort_values('Observed Requests', ascending=False)
        elif sort_by == "Risk Level":
            df_encyclopedia = df_encyclopedia.sort_values('Risk Level', ascending=False) 
        else:
            df_encyclopedia = df_encyclopedia.sort_values('Bot Name')

        # Display Cards
        st.markdown(f"Found **{len(df_encyclopedia)}** bots.")
        
        for _, row in df_encyclopedia.iterrows():
            traffic_status = "⚫ Not Seen"
            if row['Observed Requests'] > 0:
                traffic_status = f"🟢 Active ({row['Observed Requests']:,} reqs)"
                
            with st.expander(f"{row['Verdict']} {row['Bot Name']}  -  {row['Category']}  [{traffic_status}]"):
                c1, c2 = st.columns([2, 1])
                with c1:
                    st.markdown(f"**Description:** {row['Description']}")
                    st.markdown(f"**Risk Assessment:** {row['Risk Level']}")
                    
                with c2:
                    if row['Observed Requests'] > 0:
                        st.markdown("### 📊 Traffic Stats")
                        st.write(f"**Requests:** {row['Observed Requests']:,}")
                        st.write(f"**IPs:** {row['Unique IPs']}")
                        st.write(f"**Last Seen:** {row['Last Seen']}")
                        st.write(f"**Errors:** {row['Errors']}")
                    else:
                        st.info("No traffic observed from this bot in the logs.")

    with tab_edit:
        st.subheader("✏️ Edit Bot Definitions")
        st.info("Changes are saved to `data/bot_config.json` and persist across restarts.")
        
        # Get ALL known bots (KB + Signatures + Observed)
        kb_bots = set(bot_manager.get_knowledge_base().keys())
        sig_bots = set()
        for sigs in bot_manager.get_signatures().values():
            sig_bots.update(sigs)
        
        # Also include observed bots from stats query above
        obs_bots = set(observed_bots.keys()) if 'observed_bots' in locals() else set()
        
        all_bots = sorted(list(kb_bots | sig_bots | obs_bots))
        
        edit_bot_name = st.selectbox("Select Bot to Edit", ["(Add New Bot)"] + all_bots)
        
        is_new = edit_bot_name == "(Add New Bot)"
        
        with st.form("edit_bot_form"):
            if is_new:
                new_name = st.text_input("Bot Name (e.g. MyCrawlerBot)")
                current_info = {}
            else:
                new_name = edit_bot_name
                # Pre-fill existing
                current_info = bot_manager.get_bot_info(new_name)
                # If bot is only in signatures/observed but not in KB, get_bot_info returns default "Unknown"
                # We might want to try to guess category from signatures if possible
                if current_info.get('category') == 'Unknown':
                    # Try to find category from signatures
                    for cat, sigs in bot_manager.get_signatures().items():
                        # Check if exact match in signatures
                        if any(s.lower() == new_name.lower() for s in sigs):
                            current_info['category'] = cat
                            break
            
            # Fields
            desc = st.text_area("Description", value=current_info.get('description', '') if not is_new else "")
            
            # Category Select
            # Get current category index if valid
            current_cat = current_info.get('category', 'Unknown')
            cat_options = list(bot_manager.get_signatures().keys())
            if 'Unknown' not in cat_options:
                cat_options.append('Unknown')
                
            try:
                cat_index = cat_options.index(current_cat)
            except ValueError:
                cat_index = 0
                
            cat = st.selectbox("Category", cat_options, index=cat_index)
            
            risk = st.slider("Risk Score (0-10)", 0, 10, value=current_info.get('risk_score', 0) if not is_new else 0)
            val = st.slider("Value Score (0-100)", 0, 100, value=current_info.get('value_score', 50) if not is_new else 50)
            
            if st.form_submit_button("Save Changes"):
                target_name = new_name if is_new else edit_bot_name
                if target_name:
                    bot_manager.update_bot_info(target_name, desc, risk, val, cat)
                    
                    # If new OR if bot exists but wasn't in signatures for this category
                    # We should ensure it's in the signatures list for detection
                    bot_manager.add_signature(cat, target_name)
                        
                    st.success(f"Saved settings for {target_name}!")
                    st.rerun()
                else:
                    st.error("Bot name is required.")

# --- Log Explorer ---
elif page == "Log Explorer":
    st.title("🔍 Log Explorer")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        search_term = st.text_input("Search (IP, URL, User-Agent, Status)")
    with col2:
        limit = st.selectbox("Rows per page", [100, 500, 1000], index=0)

    # Pagination
    if st.button("Previous Page") and st.session_state.pagination_offset > 0:
        st.session_state.pagination_offset -= limit
    if st.button("Next Page"):
        st.session_state.pagination_offset += limit

    offset = st.session_state.pagination_offset
    
    base_query = f"SELECT * FROM access_logs WHERE {date_filter}"
    
    if search_term:
        base_query += f" AND (url ILIKE '%{search_term}%' OR client_ip ILIKE '%{search_term}%' OR user_agent ILIKE '%{search_term}%' OR toString(status_code) ILIKE '%{search_term}%')"
    
    base_query += f" ORDER BY timestamp DESC LIMIT {limit} OFFSET {offset}"
    
    df_logs = run_query(base_query)
    
    st.caption(f"Showing rows {offset} to {offset + len(df_logs)}")
    st.dataframe(df_logs, use_container_width=True)
    download_csv(df_logs, "raw_logs.csv")
