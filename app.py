from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, send_from_directory
from flask_session import Session
from flask_socketio import SocketIO, emit
import json
import random
import os
import tempfile
from datetime import datetime, timedelta

app = Flask(__name__, static_url_path='/static', static_folder='static')
app.secret_key = 'supersecretkey'
socketio = SocketIO(app)

# Statik dosya konfigürasyonu
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # Cache'i devre dışı bırak
app.config['STATIC_FOLDER'] = 'static'

# Flask-Session yapılandırması
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = os.path.join(tempfile.gettempdir(), 'flask_session')
app.config['SESSION_FILE_THRESHOLD'] = 100
app.config['PERMANENT_SESSION_LIFETIME'] = 1800  # 30 dakika
Session(app)

# Veri dosyalarının yolları
DATA_PATH = "data/sinema_tabu_karisik_150.json"
USER_WORDS_PATH = "data/user_words.json"
DISABLED_WORDS_PATH = "data/disabled_words.json"  # Yeni dosya yolu

# Oyun durumlarını saklamak için global değişken
game_states = {}

def load_disabled_words():
    """Devre dışı bırakılan kelimelerin ID'lerini yükler"""
    try:
        if not os.path.exists(DISABLED_WORDS_PATH):
            with open(DISABLED_WORDS_PATH, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=2)
            return []
        
        with open(DISABLED_WORDS_PATH, "r", encoding="utf-8") as f:
            disabled_ids = json.load(f)
            return disabled_ids if isinstance(disabled_ids, list) else []
    except (json.JSONDecodeError, FileNotFoundError):
        return []

def save_disabled_words(disabled_ids):
    """Devre dışı bırakılan kelimelerin ID'lerini kaydeder"""
    with open(DISABLED_WORDS_PATH, "w", encoding="utf-8") as f:
        json.dump(disabled_ids, f, ensure_ascii=False, indent=2)

def load_official_words():
    """Resmi kelime listesini yükler"""
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            words = json.load(f)
            return words if isinstance(words, list) else [words] if words else []
    except (json.JSONDecodeError, FileNotFoundError):
        return []

def load_user_words():
    """Kullanıcı kelime listesini yükler"""
    try:
        if not os.path.exists(USER_WORDS_PATH):
            with open(USER_WORDS_PATH, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=2)
            return []
        
        with open(USER_WORDS_PATH, "r", encoding="utf-8") as f:
            words = json.load(f)
            return words if isinstance(words, list) else [words] if words else []
    except (json.JSONDecodeError, FileNotFoundError):
        return []

def save_user_words(words):
    """Kullanıcı kelime listesini kaydeder"""
    with open(USER_WORDS_PATH, "w", encoding="utf-8") as f:
        json.dump(words, f, ensure_ascii=False, indent=2)

def merge_words(official_words, user_words, disabled_ids):
    """Resmi ve kullanıcı kelimelerini birleştirir ve devre dışı durumlarını ekler"""
    merged = []
    user_word_ids = {w["id"]: w for w in user_words}
    
    # Önce resmi kelimeleri ekle
    for word in official_words:
        word_id = word["id"]
        if word_id in user_word_ids:
            # Kullanıcı tarafından değiştirilmiş kelimeyi kullan
            word = user_word_ids[word_id].copy()
            del user_word_ids[word_id]
        else:
            word = word.copy()
        
        # Devre dışı durumunu ekle
        word["disabled"] = word_id in disabled_ids
        merged.append(word)
    
    # Kalan kullanıcı kelimelerini ekle
    for word in user_word_ids.values():
        word = word.copy()
        word["disabled"] = word["id"] in disabled_ids
        merged.append(word)
    
    return merged

def load_all_words():
    """Tüm kelimeleri (aktif ve devre dışı) yükler"""
    # Resmi kelimeleri yükle
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            official_words = json.load(f)
            if not isinstance(official_words, list):
                official_words = [official_words]
    except (json.JSONDecodeError, FileNotFoundError):
        official_words = []
    
    # Kullanıcı kelimelerini yükle veya oluştur
    try:
        if not os.path.exists(USER_WORDS_PATH):
            with open(USER_WORDS_PATH, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=2)
            user_words = []
        else:
            with open(USER_WORDS_PATH, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    user_words = []
                else:
                    user_words = json.loads(content)
                    if not isinstance(user_words, list):
                        user_words = [user_words] if user_words else []
    except (json.JSONDecodeError, FileNotFoundError):
        user_words = []
    
    # Tüm kelimeleri birleştir
    all_words = official_words + user_words
    
    # Resim URL'lerini düzelt
    for word in all_words:
        if word.get("image_url"):
            word["resim"] = word["image_url"]
    
    return all_words

def get_next_word_id():
    """Yeni kelime için ID belirler"""
    try:
        with open(USER_WORDS_PATH, "r", encoding="utf-8") as f:
            user_words = json.load(f)
            if not isinstance(user_words, list):
                user_words = [user_words] if user_words else []
            if not user_words:
                return 200  # İlk kullanıcı kelimesi için başlangıç ID'si
            return max(word["id"] for word in user_words) + 1
    except (FileNotFoundError, json.JSONDecodeError):
        return 200  # Dosya yoksa veya boşsa başlangıç ID'si

def get_user_words():
    """Sadece kullanıcı kelimelerini yükler"""
    try:
        # Dosya yoksa veya boşsa boş liste döndür
        if not os.path.exists(USER_WORDS_PATH) or os.path.getsize(USER_WORDS_PATH) == 0:
            return []
        
        with open(USER_WORDS_PATH, "r", encoding="utf-8") as f:
            content = f.read().strip()
            # Dosya boşsa veya sadece boşluk karakterleri içeriyorsa boş liste döndür
            if not content:
                return []
            
            user_words = json.loads(content)
            if not isinstance(user_words, list):
                user_words = [user_words] if user_words else []
            return user_words
    except (json.JSONDecodeError, FileNotFoundError):
        # JSON decode hatası veya dosya bulunamama durumunda boş liste döndür
        return []

@app.route("/")
def index():
    """Ana sayfa"""
    return render_template("index.html")

@app.route('/start_game', methods=['POST'])
def start_game():
    duration = int(request.form.get('duration', 60))
    passes = int(request.form.get('passes', 3))
    selected_categories = request.form.getlist('categories')
    
    if not selected_categories:
        flash('Lütfen en az bir kategori seçin', 'error')
        return redirect(url_for('index'))
    
    session['duration'] = duration
    session['passes'] = passes
    session['total_passes'] = passes  # Toplam pas hakkını kaydet
    session['selected_categories'] = selected_categories
    session['score'] = {'correct': 0, 'taboo': 0}
    session['remaining_passes'] = passes
    session['current'] = 0
    
    # Seçilen kategorilere göre kelimeleri filtrele
    words = load_words()
    filtered_words = [word for word in words if word['kategori'] in selected_categories]
    random.shuffle(filtered_words)
    session['words'] = filtered_words
    
    # Oyun durumunu başlat
    game_id = str(datetime.now().timestamp())
    game_states[game_id] = {
        "duration": duration,
        "end_time": datetime.now() + timedelta(seconds=duration),
        "score": session['score'],
        "passes": passes,
        "current": 0,
        "words": filtered_words
    }
    session["game_id"] = game_id
    
    return redirect(url_for('game'))

@app.route("/game")
def game():
    """Oyun sayfası"""
    if "words" not in session:
        return redirect(url_for("index"))
    
    if session["current"] >= len(session["words"]):
        return redirect(url_for("game_over"))
    
    word = session["words"][session["current"]]
    game_state = game_states.get(session["game_id"], {})
    remaining_time = max(0, int((game_state.get("end_time", datetime.now()) - datetime.now()).total_seconds()))
    
    # Resim URL'sini kontrol et ve düzelt
    image_url = word.get("resim", word.get("image_url", ""))
    
    # Kelime verilerini düzenle
    word_data = {
        "word": word["isim"],
        "category": word["kategori"],
        "forbidden_words": word["yasaklılar"],
        "image_url": image_url
    }
    
    return render_template("game.html", 
                         word=word_data, 
                         remaining=session["passes"],
                         duration=remaining_time)

@socketio.on('next_word')
def handle_next_word(data):
    """WebSocket üzerinden sonraki kelimeye geçer"""
    game_id = session.get("game_id")
    if not game_id or game_id not in game_states:
        return
    
    game_state = game_states[game_id]
    action = data.get("action")
    
    if action == "correct":
        game_state["score"]["correct"] += 1
    elif action == "taboo":
        game_state["score"]["taboo"] += 1
    elif action == "pass":
        if game_state["passes"] > 0:
            game_state["passes"] -= 1
        else:
            # Pas hakkı yoksa işlem yapma
            return
    
    game_state["current"] += 1
    session["current"] = game_state["current"]
    session["score"] = game_state["score"]
    session["passes"] = game_state["passes"]
    
    if game_state["current"] >= len(game_state["words"]):
        emit('game_over', {
            'score': game_state["score"]["correct"] - game_state["score"]["taboo"],
            'correct': game_state["score"]["correct"],
            'wrong': game_state["score"]["taboo"],
            'skipped': game_state["passes"]
        })
        return
    
    next_word = game_state["words"][game_state["current"]]
    remaining_time = max(0, int((game_state["end_time"] - datetime.now()).total_seconds()))
    
    # Resim URL'sini kontrol et ve düzelt
    image_url = next_word.get("resim", next_word.get("image_url", ""))
    
    emit('word', {
        'word': next_word["isim"],
        'category': next_word["kategori"],
        'forbidden_words': next_word["yasaklılar"],
        'image_url': image_url
    })
    
    emit('timer', {'time': remaining_time})
    emit('passes', {'passes': game_state["passes"]})
    emit('score', {'score': game_state["score"]["correct"] - game_state["score"]["taboo"]})

@socketio.on('game_over')
def handle_game_over():
    """Oyunu bitirir ve sonuçları gönderir"""
    game_id = session.get("game_id")
    if not game_id or game_id not in game_states:
        return
    
    game_state = game_states[game_id]
    total_passes = session.get("total_passes", 0)  # Başlangıçtaki pas hakkı
    used_passes = total_passes - game_state["passes"]  # Kullanılan pas hakkı
    
    emit('game_over', {
        'score': game_state["score"]["correct"] - game_state["score"]["taboo"],
        'correct': game_state["score"]["correct"],
        'wrong': game_state["score"]["taboo"],
        'skipped': used_passes  # Kullanılan pas hakkını gönder
    })

@app.route("/game_over")
def game_over():
    """Oyun sonu sayfası"""
    if "score" not in session:
        return redirect(url_for("index"))
    
    score = session["score"]
    return render_template("game_over.html", score=score)

@app.route("/settings")
def settings():
    """Ayarlar ana sayfası"""
    return render_template("settings.html")

@app.route("/word_settings")
def word_settings():
    """Kelime ayarları sayfası"""
    try:
        official_words = load_official_words()
        user_words = load_user_words()
        disabled_ids = load_disabled_words()
        words = merge_words(official_words, user_words, disabled_ids)
        
        # Kelimeleri ID'ye göre sırala
        words.sort(key=lambda x: x.get("id", 0))
        
        return render_template("word_settings.html", words=words)
    except Exception as e:
        print(f"Error in word_settings: {str(e)}")
        flash("Kelime listesi yüklenirken bir hata oluştu", "error")
        return redirect(url_for("index"))

@app.route("/user_dictionary")
def user_dictionary():
    """Kullanıcı sözlüğü sayfası"""
    user_words = get_user_words()
    return render_template("user_dictionary.html", user_words=user_words)

@app.route("/delete_word/<int:word_id>", methods=["POST"])
def delete_word(word_id):
    """Kullanıcı kelimesini siler"""
    user_words = get_user_words()
    user_words = [w for w in user_words if w["id"] != word_id]
    
    with open(USER_WORDS_PATH, "w", encoding="utf-8") as f:
        json.dump(user_words, f, ensure_ascii=False, indent=2)
    
    return jsonify(success=True)

@app.route("/clear_user_dictionary", methods=["POST"])
def clear_user_dictionary():
    """Tüm kullanıcı kelimelerini siler"""
    with open(USER_WORDS_PATH, "w", encoding="utf-8") as f:
        json.dump([], f, ensure_ascii=False, indent=2)
    
    return jsonify(success=True)

@app.route("/toggle_word/<int:word_id>", methods=["POST"])
def toggle_word(word_id):
    """Kelimeyi devre dışı bırakır veya etkinleştirir"""
    try:
        # Devre dışı ID'lerini yükle
        disabled_ids = load_disabled_words()
        
        # Durumu değiştir
        if word_id in disabled_ids:
            disabled_ids.remove(word_id)
            new_state = False
        else:
            disabled_ids.append(word_id)
            new_state = True
        
        # Değişiklikleri kaydet
        save_disabled_words(disabled_ids)
        
        return jsonify({
            "success": True,
            "new_state": new_state,
            "word_id": word_id
        })
    except Exception as e:
        print(f"Error in toggle_word: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/add_word', methods=['GET', 'POST'])
def add_word():
    if request.method == 'POST':
        try:
            word_data = {
                "isim": request.form['word'],
                "kategori": request.form['category'],
                "yasaklılar": request.form['forbidden'].split(','),
                "image_url": request.form.get('image_url', '')  # Resim URL'sini al
            }
            
            # Kullanıcı kelimeleri dosyasını kontrol et
            if not os.path.exists('data/user_words.json'):
                with open('data/user_words.json', 'w', encoding='utf-8') as f:
                    json.dump([], f)
            
            # Mevcut kelimeleri oku
            with open('data/user_words.json', 'r', encoding='utf-8') as f:
                words = json.load(f)
            
            # Yeni kelimeyi ekle
            words.append(word_data)
            
            # Güncellenmiş listeyi kaydet
            with open('data/user_words.json', 'w', encoding='utf-8') as f:
                json.dump(words, f, ensure_ascii=False, indent=4)
            
            flash('Kelime başarıyla eklendi!', 'success')
            return redirect(url_for('add_word'))
        except Exception as e:
            flash(f'Kelime eklenirken bir hata oluştu: {str(e)}', 'error')
            return redirect(url_for('add_word'))
    
    return render_template('add_word.html')

@app.route('/edit_word/<int:word_id>', methods=['GET', 'POST'])
def edit_word(word_id):
    """Kelime düzenleme sayfası"""
    words = load_all_words()
    word = next((w for w in words if w['id'] == word_id), None)
    
    if not word:
        flash('Kelime bulunamadı', 'error')
        return redirect(url_for('word_settings'))
    
    if request.method == 'POST':
        # Form verilerini al
        new_word = request.form.get('word')
        new_category = request.form.get('category')
        new_forbidden = request.form.get('forbidden', '').split(',')
        new_image_url = request.form.get('image_url', '')
        
        # Verileri temizle
        new_word = new_word.strip()
        new_category = new_category.strip()
        new_forbidden = [w.strip() for w in new_forbidden if w.strip()]
        new_image_url = new_image_url.strip()
        
        # Verileri güncelle
        word['isim'] = new_word
        word['kategori'] = new_category
        word['yasaklılar'] = new_forbidden
        if new_image_url:
            word['resim'] = new_image_url
            word['image_url'] = new_image_url
        
        # Kullanıcı kelimelerini güncelle
        user_words = get_user_words()
        for i, w in enumerate(user_words):
            if w['id'] == word_id:
                user_words[i] = word
                break
        
        # Dosyaya kaydet
        with open(USER_WORDS_PATH, 'w', encoding='utf-8') as f:
            json.dump(user_words, f, ensure_ascii=False, indent=2)
        
        flash('Kelime başarıyla güncellendi', 'success')
        return redirect(url_for('word_settings'))
    
    # GET isteği için form verilerini hazırla
    word_data = {
        'word': word['isim'],
        'category': word['kategori'],
        'forbidden': ', '.join(word['yasaklılar']),
        'image_url': word.get('resim', word.get('image_url', ''))
    }
    
    return render_template('edit_word.html', word=word_data, word_id=word_id)

def calculate_stats():
    """Kelime istatistiklerini hesaplar"""
    official_words = load_official_words()
    user_words = load_user_words()
    disabled_ids = load_disabled_words()
    all_words = merge_words(official_words, user_words, disabled_ids)
    
    # Genel istatistikler
    total_words = len(all_words)
    active_words = len([w for w in all_words if not w["disabled"]])
    disabled_words = total_words - active_words
    
    # Kategori bazlı istatistikler
    category_counts = {}
    category_status = {}
    
    for word in all_words:
        category = word["kategori"]
        
        # Kategori sayılarını güncelle
        category_counts[category] = category_counts.get(category, 0) + 1
        
        # Kategori durumlarını güncelle
        if category not in category_status:
            category_status[category] = {"active": 0, "disabled": 0}
        
        if word["disabled"]:
            category_status[category]["disabled"] += 1
        else:
            category_status[category]["active"] += 1
    
    return {
        "total_words": total_words,
        "active_words": active_words,
        "disabled_words": disabled_words,
        "category_counts": category_counts,
        "category_status": category_status,
        "all_words": all_words
    }

@app.route("/stats")
def stats():
    """İstatistikler sayfası"""
    stats_data = calculate_stats()
    words = load_all_words()  # Tüm kelimeleri yükle
    return render_template("stats.html", stats=stats_data, words=words)

def load_words():
    """Oyun için aktif kelimeleri yükler"""
    official_words = load_official_words()
    user_words = load_user_words()
    disabled_ids = load_disabled_words()
    all_words = merge_words(official_words, user_words, disabled_ids)
    
    # Sadece aktif kelimeleri döndür
    active_words = [w for w in all_words if not w.get("disabled", False)]
    
    # Resim URL'lerini düzelt
    for word in active_words:
        if word.get("image_url"):
            word["resim"] = word["image_url"]
    
    return active_words

if __name__ == "__main__":
    socketio.run(app, debug=True)
