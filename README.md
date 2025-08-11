# 🎬 Cinema Taboo (Sinema Tabu)

An interactive, event-friendly “Taboo”-style guessing game focused on cinema, built with **Python (Flask)** and a simple **HTML/CSS** frontend.  
Originally created for the **Konya Technical University Cinema Club** (*Konya Teknik Üniversitesi Sinema Topluluğu*) to use during club events.

---

## ✨ Features

- **Web-based UI (Flask):** Runs locally in the browser; easy to project on a screen.
- **Cinema-themed cards:** Each round shows a movie title with **forbidden words**.
- **Editable dataset:** Add or change films and taboo words under `data/`.
- **Lightweight stack:** Plain templates in `templates/` and styles under `static/`.

---

## 🚀 Quick Start

1) **Clone**
```bash
git clone https://github.com/alpadalar/sinema-tabu.git
cd sinema-tabu
```

2) **Create a virtual environment (recommended)**
```bash
python3 -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

3) **Install dependencies**
```bash
pip install -r requirements.txt
```

4) **Run (choose one)**
- Using Flask CLI:
```bash
flask --app app run --debug
```
- Or directly:
```bash
python app.py
```

Then open: **http://127.0.0.1:5000**

---

## 🧩 How to Play

1. The app shows a **film title** and several **forbidden words**.  
2. The clue-giver explains the film **without** saying any forbidden words.  
3. Teammates guess the film.  
4. Move to the next card and keep the round flowing!

---

## 📂 Project Structure (overview)

```
sinema-tabu/
├─ app.py
├─ wsgi.py
├─ requirements.txt
├─ data/           # movie titles & taboo words
├─ templates/      # Flask templates (HTML)
└─ static/         # CSS/JS/assets
```

---

## 🗃️ Data

- All cards are stored under **`data/`**.  
- You can extend or modify the dataset to match your event theme (e.g., Turkish cinema, Oscar winners, sci-fi classics).
- After editing the data, simply refresh the page to use the new deck.

> Tip: Keep clues challenging but fair—avoid overly obscure titles if you’ll play with mixed audiences.

---

## 🛠️ Customization Ideas

- **Round timer** and **scoreboard** for competitive play.
- **Theme decks** (e.g., *Yeşilçam*, *Animation*, *Thrillers*).
- **Keyboard shortcuts** for next/previous card while presenting.
- **Deployment** with a WSGI server (e.g., `gunicorn "wsgi:app"`).

---

## 🤝 Contributing

Pull requests are welcome:
- Add new movie decks
- Improve UI/UX
- Add features (timer, scoring, team modes)

---

## 📜 License

No license file is currently included. Consider adding one (e.g., MIT) so others know how they can use and contribute.

---

## 🙌 Credits

Developed by **Alperen Adalar** for the **Konya Technical University Cinema Club**.
