import sqlite3
import hashlib
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, '/home/ubuntu/newslancashire/scripts')
from crawler_v3 import get_db

AIDOGE_DATA = '/home/ubuntu/aidoge/data'

def generate_crime_report():
    reports = []
    councils = ['burnley', 'hyndburn', 'pendle']
    
    for council in councils:
        crime_file = f'{AIDOGE_DATA}/{council}/crime_stats.json'
        if not os.path.exists(crime_file):
            continue
        
        with open(crime_file) as f:
            data = json.load(f)
        
        borough = data.get('borough_name', council.title())
        date = data.get('date', 'Unknown')
        total_crimes = data.get('total_crimes', 0)
        categories = data.get('by_category', {})
        outcomes = data.get('outcomes', {})
        
        top_crimes = sorted(categories.items(), key=lambda x: x[1], reverse=True)[:5]
        investigation_complete = outcomes.get('Investigation complete; no suspect identified', 0)
        total_outcomes = sum(outcomes.values()) if outcomes else 1
        unresolved_rate = (investigation_complete / total_outcomes * 100) if total_outcomes else 0
        
        title = f"Crime in {borough}: {total_crimes} offences reported in {date}"
        
        crime_names = {
            'violent-crime': 'violent crime',
            'anti-social-behaviour': 'anti-social behaviour',
            'burglary': 'burglary',
            'criminal-damage-arson': 'criminal damage',
            'shoplifting': 'shoplifting',
            'vehicle-crime': 'vehicle crime'
        }
        
        if not top_crimes:
            continue
            
        crime1_name = crime_names.get(top_crimes[0][0], top_crimes[0][0].replace('-', ' '))
        crime2_name = crime_names.get(top_crimes[1][0], top_crimes[1][0].replace('-', ' ')) if len(top_crimes) > 1 else 'other crime'
        
        summary = f"{total_crimes} crimes were reported in {borough} during {date}. The most common offences were {crime1_name} ({top_crimes[0][1]} cases), followed by {crime2_name} ({top_crimes[1][1]} cases). Police resolved {100-unresolved_rate:.0f}% of cases."
        
        article_id = hashlib.md5(f'crime-{council}-{date}'.encode()).hexdigest()
        
        borough_flags = {f'is_{c}': 1 if c == council else 0 for c in 
                        ['burnley', 'hyndburn', 'pendle', 'blackpool', 'preston', 'lancaster', 
                         'rossendale', 'ribble_valley', 'blackburn', 'chorley', 'south_ribble',
                         'west_lancashire', 'wyre', 'fylde']}
        
        reports.append({
            'id': article_id, 'title': title, 'link': f'https://aidoge.co.uk/{council}/#crime',
            'source': f'{borough} Police Data (AI DOGE)', 'source_type': 'data_journalism',
            'published': datetime.now().isoformat(), 'summary': summary, 'ai_rewrite': summary,
            'category': 'crime', 'interest_score': 75, 'trending_score': 60,
            'content_tier': 'data_driven', 'author': 'Data Analysis',
            'search_text': f'{title} {summary}'.lower(), **borough_flags
        })
    
    return reports

def generate_spending_digest():
    reports = []
    councils = ['burnley', 'hyndburn', 'pendle']
    
    for council in councils:
        spending_file = f'{AIDOGE_DATA}/{council}/spending.json'
        if not os.path.exists(spending_file):
            continue
        
        try:
            with open(spending_file) as f:
                data = json.load(f)
        except:
            continue
        
        transactions = data.get('data', [])
        if not transactions:
            continue
        
        recent = transactions[:100]
        total_spent = sum(float(t.get('amount', 0)) for t in recent)
        top_payments = sorted(recent, key=lambda x: float(x.get('amount', 0)), reverse=True)[:3]
        
        borough = council.title()
        title = f"{borough} Council: £{total_spent/1e6:.1f}M in recent spending"
        
        top_suppliers = []
        for t in top_payments:
            supplier = t.get('supplier', 'Unknown')[:25]
            amount = float(t.get('amount', 0))/1000
            top_suppliers.append(f"£{amount:.0f}k to {supplier}")
        
        summary = f"{borough} Borough Council processed {len(recent)} payments totalling £{total_spent/1e6:.2f}million. Largest payments included: {', '.join(top_suppliers)}. Data from AI DOGE."
        
        article_id = hashlib.md5(f'spending-{council}-{datetime.now().strftime("%Y-%m-%d")}'.encode()).hexdigest()
        
        borough_flags = {f'is_{c}': 1 if c == council else 0 for c in 
                        ['burnley', 'hyndburn', 'pendle', 'blackpool', 'preston', 'lancaster', 
                         'rossendale', 'ribble_valley', 'blackburn', 'chorley', 'south_ribble',
                         'west_lancashire', 'wyre', 'fylde']}
        
        reports.append({
            'id': article_id, 'title': title, 'link': f'https://aidoge.co.uk/{council}/',
            'source': f'{borough} Spending Data (AI DOGE)', 'source_type': 'data_journalism',
            'published': datetime.now().isoformat(), 'summary': summary, 'ai_rewrite': summary,
            'category': 'politics', 'interest_score': 65, 'trending_score': 45,
            'content_tier': 'data_driven', 'author': 'Data Analysis',
            'search_text': f'{title} {summary}'.lower(), **borough_flags
        })
    
    return reports

def generate_budget_report():
    reports = []
    comparison_file = f'{AIDOGE_DATA}/reference/cross_council_comparison.json'
    
    if not os.path.exists(comparison_file):
        return reports
    
    with open(comparison_file) as f:
        data = json.load(f)
    
    for council_id, council_data in data.get('councils', {}).items():
        name = council_data.get('name', council_id.title())
        trends = council_data.get('trends', {})
        
        total_spending = trends.get('Total Net Current Expenditure', [])
        if len(total_spending) < 2:
            continue
        
        latest = total_spending[-1]
        previous = total_spending[-2]
        
        # Handle None values (Pendle missing 2023-24 data)
        latest_val = latest.get('value')
        previous_val = previous.get('value')
        
        if latest_val is None or previous_val is None:
            continue
        
        try:
            change = ((float(latest_val) - float(previous_val)) / float(previous_val) * 100)
        except:
            continue
        
        direction = 'rose' if change > 0 else 'fell'
        
        title = f"{name} Council spending {direction} {abs(change):.1f}% to £{latest_val/1000:.1f}M"
        
        summary = f"{name} Borough Council's net current expenditure {direction} by £{abs(latest_val - previous_val)/1000:.1f}million ({abs(change):.1f}%) in {latest['year']}, according to GOV.UK data. Total spending reached £{latest_val/1000:.1f}million, compared to £{previous_val/1000:.1f}million in {previous['year']}."
        
        article_id = hashlib.md5(f'budget-{council_id}-{latest["year"]}'.encode()).hexdigest()
        
        borough_flags = {f'is_{c}': 1 if c == council_id else 0 for c in 
                        ['burnley', 'hyndburn', 'pendle', 'blackpool', 'preston', 'lancaster', 
                         'rossendale', 'ribble_valley', 'blackburn', 'chorley', 'south_ribble',
                         'west_lancashire', 'wyre', 'fylde']}
        
        reports.append({
            'id': article_id, 'title': title, 'link': f'https://aidoge.co.uk/{council_id}/',
            'source': 'GOV.UK Budget Data (AI DOGE)', 'source_type': 'data_journalism',
            'published': datetime.now().isoformat(), 'summary': summary, 'ai_rewrite': summary,
            'category': 'politics', 'interest_score': 70, 'trending_score': 50,
            'content_tier': 'data_driven', 'author': 'Data Analysis',
            'search_text': f'{title} {summary}'.lower(), **borough_flags
        })
    
    return reports

def insert_article(conn, article):
    conn.execute('''
        INSERT OR IGNORE INTO articles 
        (id, title, link, source, source_type, published, summary, ai_rewrite,
         category, content_tier, interest_score, trending_score, author, search_text,
         is_burnley, is_hyndburn, is_pendle, is_rossendale, is_ribble_valley,
         is_blackburn, is_chorley, is_south_ribble, is_preston, is_west_lancashire,
         is_lancaster, is_wyre, is_fylde, is_blackpool)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        article['id'], article['title'], article['link'], article['source'],
        article['source_type'], article['published'], article['summary'], article['ai_rewrite'],
        article['category'], article['content_tier'], article['interest_score'], article['trending_score'],
        article['author'], article['search_text'],
        article['is_burnley'], article['is_hyndburn'], article['is_pendle'], article['is_rossendale'],
        article['is_ribble_valley'], article['is_blackburn'], article['is_chorley'], article['is_south_ribble'],
        article['is_preston'], article['is_west_lancashire'], article['is_lancaster'], article['is_wyre'],
        article['is_fylde'], article['is_blackpool']
    ))
    conn.commit()

def main():
    print('=== Data Journalist ===')
    conn = get_db()
    total_new = 0
    
    print('\nGenerating crime reports...')
    for article in generate_crime_report():
        try:
            insert_article(conn, article)
            total_new += 1
            print(f'  Added: {article["title"][:60]}...')
        except sqlite3.IntegrityError:
            print(f'  Exists: {article["title"][:60]}...')
        except Exception as e:
            print(f'  Error: {e}')
    
    print('\nGenerating spending digests...')
    for article in generate_spending_digest():
        try:
            insert_article(conn, article)
            total_new += 1
            print(f'  Added: {article["title"][:60]}...')
        except sqlite3.IntegrityError:
            print(f'  Exists: {article["title"][:60]}...')
        except Exception as e:
            print(f'  Error: {e}')
    
    print('\nGenerating budget reports...')
    for article in generate_budget_report():
        try:
            insert_article(conn, article)
            total_new += 1
            print(f'  Added: {article["title"][:60]}...')
        except sqlite3.IntegrityError:
            print(f'  Exists: {article["title"][:60]}...')
        except Exception as e:
            print(f'  Error: {e}')
    
    print(f'\nTotal new data-driven articles: {total_new}')
    conn.close()

if __name__ == '__main__':
    main()
