# 🚀 Complete Deployment Guide for WriterAI

## Overview

WriterAI is a **Python FastAPI web application**, not a static website. It requires a Python runtime environment to function. This guide covers all deployment options from local development to cloud hosting.

## 📋 Prerequisites

- Python 3.10 or higher
- OpenAI API key (required)
- Git installed
- Basic command line knowledge

---

## 🎯 Quick Deploy Options

### Option 1: Deploy to Render (Recommended - Free Tier Available)

**Why Render?**
- ✅ Free tier with 750 hours/month
- ✅ Automatic HTTPS
- ✅ GitHub integration
- ✅ Zero configuration needed (uses `render.yaml`)
- ✅ Automatic deployments on git push

**Steps:**

1. **Fork the repository** on GitHub to your account

2. **Sign up** at [https://render.com](https://render.com)

3. **Create new Web Service:**
   - Click "New +" → "Web Service"
   - Connect your GitHub account
   - Select your WriterAI repository
   - Render will auto-detect settings from `render.yaml`

4. **Add Environment Variables:**
   - In the Render dashboard, go to "Environment"
   - Add: `OPENAI_API_KEY` with your OpenAI API key
   - Add: `WRITERAI_API_KEY` (auto-generated) or set your own

5. **Deploy:**
   - Click "Create Web Service"
   - Wait 5-10 minutes for first deployment
   - Your app will be live at: `https://your-app-name.onrender.com`

6. **Access the Dashboard:**
   - Navigate to your Render URL
   - You'll see the beautiful WriterAI dashboard
   - Create your first novel project!

**Configuration Details (already in `render.yaml`):**
```yaml
buildCommand: "cd prometheus_novel && pip install poetry && poetry install --no-dev"
startCommand: "cd prometheus_novel && poetry run uvicorn interfaces.web.app:app --host 0.0.0.0 --port $PORT"
healthCheckPath: /api/v2/health
```

---

### Option 2: Deploy to Railway

**Why Railway?**
- ✅ Simple deployment process
- ✅ Pay-as-you-go pricing ($5/month typical)
- ✅ Great performance
- ✅ Easy environment management

**Steps:**

1. **Install Railway CLI:**
   ```bash
   npm install -g @railway/cli
   # or use: brew install railway
   ```

2. **Login and initialize:**
   ```bash
   railway login
   cd WriterAI
   railway init
   ```

3. **Set environment variables:**
   ```bash
   railway variables set OPENAI_API_KEY=your_key_here
   ```

4. **Deploy:**
   ```bash
   railway up
   ```

5. **Get your URL:**
   ```bash
   railway domain
   ```

Your app will be live at the provided Railway domain!

---

### Option 3: Deploy to Heroku

**Why Heroku?**
- ✅ Classic PaaS platform
- ✅ Extensive add-ons ecosystem
- ✅ Easy scaling
- ✅ $7/month basic tier

**Steps:**

1. **Install Heroku CLI:**
   ```bash
   brew install heroku/brew/heroku  # macOS
   # or download from https://devcenter.heroku.com/articles/heroku-cli
   ```

2. **Login and create app:**
   ```bash
   heroku login
   cd WriterAI
   heroku create your-writerai-app
   ```

3. **Set environment variables:**
   ```bash
   heroku config:set OPENAI_API_KEY=your_key_here
   ```

4. **Deploy:**
   ```bash
   git push heroku main
   ```

5. **Open your app:**
   ```bash
   heroku open
   ```

The `Procfile` is already configured:
```
web: cd prometheus_novel && uvicorn interfaces.web.app:app --host 0.0.0.0 --port $PORT
```

---

### Option 4: Deploy to Fly.io

**Why Fly.io?**
- ✅ Global edge network
- ✅ Low latency worldwide
- ✅ Docker-based deployment
- ✅ Free allowance included

**Steps:**

1. **Install Fly CLI:**
   ```bash
   curl -L https://fly.io/install.sh | sh
   ```

2. **Login and launch:**
   ```bash
   fly auth login
   cd WriterAI
   fly launch
   ```

3. **Set secrets:**
   ```bash
   fly secrets set OPENAI_API_KEY=your_key_here
   ```

4. **Deploy:**
   ```bash
   fly deploy
   ```

The `fly.toml` configuration is already included in the repository.

---

### Option 5: Docker Deployment

**Why Docker?**
- ✅ Deploy anywhere that supports containers
- ✅ Consistent environment
- ✅ Easy to scale
- ✅ Works with AWS, GCP, Azure, DigitalOcean, etc.

**Steps:**

1. **Build the image:**
   ```bash
   cd WriterAI
   docker build -t writerai:latest .
   ```

2. **Run locally:**
   ```bash
   docker run -d -p 8080:8080 \
     -e OPENAI_API_KEY=your_key_here \
     --name writerai \
     writerai:latest
   ```

3. **Access the app:**
   - Open: http://localhost:8080
   - Dashboard should load immediately

4. **View logs:**
   ```bash
   docker logs -f writerai
   ```

5. **Stop the container:**
   ```bash
   docker stop writerai
   docker rm writerai
   ```

**Deploy to Docker Hub:**
```bash
docker tag writerai:latest yourusername/writerai:latest
docker push yourusername/writerai:latest
```

Then deploy to any cloud platform that supports Docker containers.

---

## 💻 Local Development

### Option A: Using Make (Recommended)

1. **Clone and setup:**
   ```bash
   git clone https://github.com/yourusername/WriterAI.git
   cd WriterAI
   ```

2. **Create `.env` file:**
   ```bash
   cp .env.example .env
   # Edit .env and add your OPENAI_API_KEY
   ```

3. **Install dependencies:**
   ```bash
   make install
   ```

4. **Run the web dashboard:**
   ```bash
   make serve-web
   ```

5. **Open browser:**
   - Navigate to: http://localhost:8080
   - You'll see the beautiful WriterAI dashboard

### Option B: Using Poetry

1. **Install Poetry:**
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

2. **Setup project:**
   ```bash
   git clone https://github.com/yourusername/WriterAI.git
   cd WriterAI/prometheus_novel
   poetry install
   ```

3. **Create `.env`:**
   ```bash
   cp .env.example .env
   # Add your OPENAI_API_KEY
   ```

4. **Run the dashboard:**
   ```bash
   poetry run uvicorn interfaces.web.app:app --reload --port 8080
   ```

### Option C: Using pip

1. **Create virtual environment:**
   ```bash
   git clone https://github.com/yourusername/WriterAI.git
   cd WriterAI
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Setup environment:**
   ```bash
   cp .env.example .env
   # Add your OPENAI_API_KEY to .env
   ```

4. **Run the application:**
   ```bash
   cd prometheus_novel
   python -m uvicorn interfaces.web.app:app --reload --port 8080
   ```

---

## 🌐 GitHub Pages (Static Landing Page Only)

**Important:** GitHub Pages only hosts static HTML/CSS/JS files. It **cannot** run the Python application.

However, we've included a beautiful landing page (`index.html`) that:
- Explains the project
- Shows features and capabilities
- Provides deployment instructions
- Links to documentation

**To enable GitHub Pages:**

1. Go to your repository settings
2. Navigate to "Pages"
3. Select source: "Deploy from a branch"
4. Choose: "main" branch, "/ (root)" folder
5. Save

Your landing page will be live at: `https://yourusername.github.io/WriterAI/`

This landing page will guide visitors to deploy their own instance of WriterAI.

---

## 🔧 Environment Variables

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `OPENAI_API_KEY` | Your OpenAI API key | `sk-...` |
| `PORT` | Port to run the server (auto-set by most platforms) | `8080` |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `WRITERAI_API_KEY` | API key for accessing WriterAI API | Auto-generated |
| `DATABASE_URL` | Database connection string | SQLite local file |
| `REDIS_URL` | Redis connection for caching | Not used by default |
| `LOG_LEVEL` | Logging level | `INFO` |
| `DEBUG` | Enable debug mode | `False` |

---

## 🎨 Accessing the Web Interface

Once deployed, your WriterAI instance will have these endpoints:

### Main Interfaces

- **Web Dashboard**: `https://your-domain.com/`
  - Beautiful UI for creating and managing projects
  - Browse story ideas
  - Monitor generation progress

- **API Documentation**: `https://your-domain.com/api/v2/docs`
  - Interactive API explorer
  - Full REST API reference
  - Test API endpoints

- **Health Check**: `https://your-domain.com/api/v2/health`
  - System status
  - Metrics and uptime

### Key Features Available

1. **Create New Projects**
   - Click "New Project"
   - Fill in title, genre, synopsis
   - Add characters and setting
   - Submit to create configuration

2. **View Projects**
   - See all your novel projects
   - Click to view details
   - Check generation status

3. **Browse Ideas**
   - Search 899 pre-loaded story ideas
   - Filter by genre and category
   - Use as inspiration

---

## 📊 Monitoring and Logs

### Render
- View logs in Render dashboard
- Real-time log streaming
- Automatic log retention

### Railway
```bash
railway logs
```

### Heroku
```bash
heroku logs --tail
```

### Docker
```bash
docker logs -f writerai
```

### Local Development
Logs are written to:
- Console (stdout)
- `logs/prometheus_novel.log`

---

## 🔒 Security Considerations

### Environment Variables
- **Never** commit `.env` files
- Use platform secret management
- Rotate API keys regularly

### API Keys
- Keep your `OPENAI_API_KEY` secure
- Set spending limits in OpenAI dashboard
- Monitor usage regularly

### Access Control
- Consider adding authentication
- Use WRITERAI_API_KEY for API access
- Implement rate limiting for production

---

## 🐛 Troubleshooting

### Application Won't Start

**Check:**
1. Python version is 3.10+
2. All environment variables are set
3. Dependencies are installed
4. Port is not in use

**View logs:**
```bash
# Render/Railway/Heroku: Check platform dashboard
# Local:
tail -f logs/prometheus_novel.log
```

### Database Errors

**Solution:**
```bash
# Initialize the ideas database
cd prometheus_novel
python prometheus_lib/utils/ideas_db.py init
```

### Import Errors

**Solution:**
```bash
# Reinstall dependencies
pip install -r requirements.txt

# Or with poetry:
cd prometheus_novel
poetry install
```

### Port Already in Use

**Solution:**
```bash
# Find and kill process using port 8080
lsof -ti:8080 | xargs kill -9

# Or use a different port:
uvicorn interfaces.web.app:app --port 8081
```

### OpenAI API Errors

**Check:**
1. API key is valid
2. You have credits in your OpenAI account
3. No rate limiting issues
4. Correct model names in config

---

## 📈 Scaling Considerations

### For Heavy Use

1. **Use a database:**
   - Switch from SQLite to PostgreSQL
   - Add `DATABASE_URL` environment variable

2. **Add Redis caching:**
   - Install Redis
   - Set `REDIS_URL` environment variable

3. **Increase workers:**
   ```bash
   uvicorn interfaces.web.app:app --workers 4
   ```

4. **Use a CDN:**
   - Serve static files from CDN
   - Reduce server load

### Cost Management

- Set OpenAI spending limits
- Use GPT-4o-mini for cost efficiency
- Monitor usage in the dashboard
- Implement usage quotas per user

---

## 🎯 Next Steps

After deployment:

1. **Access your dashboard** at your deployed URL
2. **Create your first project** using the web interface
3. **Generate a novel** using the CLI or API
4. **Export to Kindle** format when complete

### CLI Commands (via SSH or local)

```bash
# Create a new project
cd prometheus_novel
python prometheus new --interactive

# Generate all stages
python prometheus generate --config configs/my_novel.yaml --all

# Export to Kindle format
python export_all_formats.py \
  --state data/my_novel/state_snapshots/latest_state.json \
  --title "My Novel" \
  --author "Your Name"
```

---

## 📚 Additional Resources

- **GitHub Repository**: Full source code and issues
- **README.md**: Project overview and quick start
- **KINDLE_EXPORT_GUIDE.md**: Publishing to Amazon KDP
- **QUICKSTART.md**: Beginner-friendly tutorial
- **API Documentation**: `/api/v2/docs` on your deployed instance

---

## 💬 Support

If you encounter issues:

1. Check the troubleshooting section above
2. Review logs for error messages
3. Search existing GitHub issues
4. Create a new issue with:
   - Deployment method used
   - Error messages
   - Steps to reproduce
   - Your environment details

---

**🎉 Congratulations on deploying WriterAI!**

Transform your story ideas into complete novels with the power of AI.

Made with ❤️ by the WriterAI Team

