#!/usr/bin/env python3
"""Re-run borough detection on all existing articles in the database."""

import sqlite3

DB_PATH = '/home/ubuntu/newslancashire/db/news.db'

BOROUGHS = {
    'burnley': ['burnley', 'padiham', 'brierfield', 'hapton', 'worsthorne'],
    'pendle': ['pendle', 'nelson', 'colne', 'barnoldswick', 'barrowford', 'earby', 'trawden'],
    'rossendale': ['rossendale', 'rawtenstall', 'bacup', 'haslingden', 'whitworth', 'helmshore'],
    'hyndburn': ['hyndburn', 'accrington', 'oswaldtwistle', 'great harwood', 'rishton', 'clayton-le-moors'],
    'ribble_valley': ['ribble valley', 'clitheroe', 'longridge', 'whalley', 'read', 'sabden'],
    'blackburn': ['blackburn', 'darwen', 'blackburn with darwen'],
    'chorley': ['chorley', 'adlington', 'euxton', 'coppull', 'whittle-le-woods'],
    'south_ribble': ['south ribble', 'leyland', 'penwortham', 'bamber bridge', 'lostock hall'],
    'preston': ['preston', 'fulwood', 'ashton-on-ribble', 'ribbleton'],
    'west_lancashire': ['west lancashire', 'ormskirk', 'skelmersdale', 'burscough', 'tarleton'],
    'lancaster': ['lancaster', 'morecambe', 'heysham', 'carnforth', 'silverdale'],
    'wyre': ['wyre', 'fleetwood', 'thornton-cleveleys', 'garstang', 'poulton-le-fylde'],
    'fylde': ['fylde', 'lytham', 'st annes', 'kirkham', 'freckleton', 'warton'],
    'blackpool': ['blackpool', 'bispham', 'south shore', 'north shore'],
}


def detect_boroughs(title, summary):
    text = (title + ' ' + (summary or '')).lower()
    result = {}
    for borough, keywords in BOROUGHS.items():
        result['is_' + borough] = 1 if any(kw in text for kw in keywords) else 0
    return result


def main():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('SELECT id, title, summary FROM articles')
    rows = c.fetchall()

    updated = 0
    for article_id, title, summary in rows:
        boroughs = detect_boroughs(title or '', summary or '')
        c.execute(
            'UPDATE articles SET '
            'is_burnley=?, is_blackpool=?, is_preston=?, is_lancaster=?, '
            'is_pendle=?, is_rossendale=?, is_hyndburn=?, is_ribble_valley=?, '
            'is_blackburn=?, is_chorley=?, is_south_ribble=?, '
            'is_west_lancashire=?, is_wyre=?, is_fylde=? '
            'WHERE id=?',
            (boroughs['is_burnley'], boroughs['is_blackpool'],
             boroughs['is_preston'], boroughs['is_lancaster'],
             boroughs['is_pendle'], boroughs['is_rossendale'],
             boroughs['is_hyndburn'], boroughs['is_ribble_valley'],
             boroughs['is_blackburn'], boroughs['is_chorley'],
             boroughs['is_south_ribble'], boroughs['is_west_lancashire'],
             boroughs['is_wyre'], boroughs['is_fylde'],
             article_id))
        updated += 1

    conn.commit()

    # Show counts per borough
    for borough in sorted(BOROUGHS.keys()):
        col = 'is_' + borough
        c.execute('SELECT COUNT(*) FROM articles WHERE ' + col + ' = 1')
        count = c.fetchone()[0]
        if count > 0:
            print(borough + ': ' + str(count) + ' articles')

    c.execute('SELECT COUNT(*) FROM articles')
    total = c.fetchone()[0]
    print('Total articles: ' + str(total))
    print('Updated: ' + str(updated))
    conn.close()


if __name__ == '__main__':
    main()
