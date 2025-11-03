````markdown
# 🎥 LivePulse — Real-Time Q&A + Polls for Streams

A lightweight, deploy-ready **Django + HTMX + Channels** app for live Q&A sessions and interactive polls.  
Viewers can submit questions and upvote in real time — hosts can approve, pin, mark answered, and run live polls with instant vote updates.

---

## ✨ Features

- ⚡ **Realtime updates** (WebSockets via Django Channels + Redis)
- 🗳️ **Live polls** with instant vote charts  
- 🙋 **Question management** — approve, reject, pin, mark answered  
- 🚦 **Rate-limit & anti-spam** protection (Redis-backed)  
- 🎨 **Clean UI** built with **Tailwind + HTMX**  
- 🧑‍💼 **Unfold Admin** for a modern Django admin experience  
- 🧰 **No Docker needed** — works out of the box  
- 🌐 **Deployable** to Render, Railway, or any ASGI host  

---

## 🚀 Quick Start

### 1️⃣ Clone & Setup
```bash
git clone https://github.com/<yourname>/livepulse.git
cd livepulse
python -m venv .venv && .venv\Scripts\activate  # or source .venv/bin/activate
pip install -r requirements.txt
````

### 2️⃣ Environment

Copy and configure your `.env`:

```bash
cp .env.example .env
```

Example:

```
SECRET_KEY=change-me
DEBUG=true
ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://localhost,http://127.0.0.1
REDIS_URL=redis://127.0.0.1:6379/0
```

### 3️⃣ Run the App

```bash
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py runserver
```

Visit ➜ `http://localhost:8000`

---

## 🧪 Demo Data

Populate with sample questions + poll:

```bash
python manage.py seed_demo
```

Then open:

* **Viewer:** `/r/<slug>/`
* **Host:** `/host/<slug>/?host=<secret>`

---

## 🧩 Tech Stack

| Layer      | Tools                 |
| ---------- | --------------------- |
| Backend    | Django 5 + Channels 4 |
| Frontend   | HTMX + Tailwind CDN   |
| Realtime   | Redis pub/sub         |
| Admin      | django-unfold         |
| Rate-limit | Custom Redis service  |
| Deployment | Daphne / ASGI app     |

---

## 📦 Project Structure

```
livepulse/
├── livepulse/          # core settings, urls, asgi
├── lipapp/             # main app (views, models, services)
├── templates/          # base.html, home, host, viewer
├── static/             # js/, css/
├── .env.example
├── requirements.txt
├── manage.py
└── README.md
```

---

## ☁️ Deploying

### Render / Railway / Fly.io

**Procfile**

```
web: daphne -b 0.0.0.0 -p $PORT livepulse.asgi:application
```

**Post-deploy**

```
python manage.py collectstatic --noinput
```

Add environment variables:

```
SECRET_KEY, DEBUG, ALLOWED_HOSTS, CSRF_TRUSTED_ORIGINS, REDIS_URL
```

---

## 🩺 Health Endpoints

| Endpoint   | Description    |
| ---------- | -------------- |
| `/healthz` | Health check   |
| `/version` | Basic metadata |

---

## 🧠 Tips

* Use `?host=<secret>` once — host session persists.
* Use Redis Cloud free tier if you don’t want Docker.
* HTMX handles live fragments (fast refresh without reload).

---

## 🧾 License

MIT © [Hossein Mohammadi Kia]

---

### ❤️ Built for fun, learning, and live interaction demos by Hossein Mohammadi Kia.

```
```
