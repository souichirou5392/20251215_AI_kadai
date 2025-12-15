NGROK_AUTH_TOKEN = "YOUR_NGROK_TOKEN" 
MY_API_KEY = "YOUR_GEMINI_API_KEY"


!pip install flask flask-cors pyngrok google-genai

import datetime as dt
import json
import requests
import xml.etree.ElementTree as ET
from flask import Flask, jsonify, request
from flask_cors import CORS
from pyngrok import ngrok, conf
from google import genai
from google.genai import types

if NGROK_AUTH_TOKEN and NGROK_AUTH_TOKEN != "ここに2Fから始まるトークンを貼り付け":
    conf.get_default().auth_token = NGROK_AUTH_TOKEN
    print("✅ ngrok認証完了")
else:
    print("⚠️ ngrokトークンが設定されていません")

MODEL_NAME = 'gemini-2.0-flash-exp'

RSS_LINKS = {
    'politics': 'https://www.nhk.or.jp/rss/news/cat5.xml',  
    'it': 'https://news.yahoo.co.jp/rss/topics/it.xml',        
    'sports': 'https://news.yahoo.co.jp/rss/topics/sports.xml' ,
}

def get_topics(rss_url):
    topics = []
    try:
        res = requests.get(rss_url)
        res.encoding = res.apparent_encoding
        root = ET.fromstring(res.text)
        items = root.findall('.//item')
        for item in items[:8]:
            title = item.find('title').text if item.find('title') is not None else ''
            link = item.find('link').text if item.find('link') is not None else ''
            description = item.find('description').text if item.find('description') is not None else ''
            
            pub_date_str = item.find('pubDate').text if item.find('pubDate') is not None else ''
            try:
                if '+' in pub_date_str:
                    pub_date = dt.datetime.strptime(pub_date_str, '%a, %d %b %Y %H:%M:%S %z')
                else:
                    pub_date = dt.datetime.strptime(pub_date_str, '%a, %d %b %Y %H:%M:%S %Z')
                pub_date_iso = pub_date.strftime('%Y/%m/%d %H:%M')
            except:
                pub_date_iso = ""
            
            topics.append({
                'title': title, 
                'link': link, 
                'description': description, 
                'pub_date': pub_date_iso
            })
    except Exception as e:
        print(f"RSS Error: {e}")
    return topics

def get_gemini_tags(text):
    client = genai.Client(api_key=MY_API_KEY)
    prompt = """
    以下のニュース記事に対し、内容を表す関連タグを1〜3個生成してください。
    出力はJSON形式のリストのみ（例: ["政治", "選挙"]）で、余計な文字は含めないでください。
    """
    config = types.GenerateContentConfig(
        system_instruction=prompt,
        max_output_tokens=100,
        temperature=0.3,
        response_mime_type="application/json"
    )
    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=text,
            config=config
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"Gemini Error: {e}")
        return ["ニュース"]

app = Flask(__name__)
CORS(app)

@app.route('/api/news')
def api_news():
    category = request.args.get('category', 'politics') # デフォルトを政治に
    rss_url = RSS_LINKS.get(category)
    
    if not rss_url: return jsonify([]), 400
    
    print(f"Fetching category: {category}")
    news_list = get_topics(rss_url)
    
    for news in news_list:
        content = f"{news['title']} {news['description']}"
        news['tags'] = get_gemini_tags(content)
        
    return jsonify(news_list)

ngrok.kill()
public_url = ngrok.connect(5000).public_url
print(f"==================================================")
print(f"新しいURL: {public_url}")
print(f"==================================================")
app.run(port=5000)