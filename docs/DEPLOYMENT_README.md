# 🚀 Quick Deployment Guide

## The Issue with GitHub Pages

**Important:** WriterAI is a **Python FastAPI application**, not a static website. GitHub Pages can only host static HTML/CSS/JS files and **cannot run Python applications**.

### What This Means:

- ✅ **GitHub Pages CAN**: Show the landing page (`index.html`) with project information
- ❌ **GitHub Pages CANNOT**: Run the actual WriterAI application (Python backend required)

## ✨ Solution: Deploy to a Python Platform

To use WriterAI's full functionality (web dashboard, API, novel generation), you need to deploy it to a platform that supports Python applications.

---

## 🎯 Recommended: One-Click Deploy to Render

**Best for:** Free tier, automatic HTTPS, GitHub integration

### Steps:

1. **Fork this repository** to your GitHub account

2. **Sign up at Render**: [https://render.com](https://render.com)

3. **Create Web Service**:
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Render auto-detects settings from `render.yaml`

4. **Add Environment Variable**:
   - Add `OPENAI_API_KEY` with your key from [OpenAI](https://platform.openai.com/api-keys)

5. **Deploy!**
   - Click "Create Web Service"
   - Wait 5-10 minutes
   - Your app will be live! 🎉

**Your WriterAI URL**: `https://your-app-name.onrender.com`

---

## 🏃 Quick Local Development

Want to run it locally first?

```bash
# Clone and setup
git clone https://github.com/yourusername/WriterAI.git
cd WriterAI

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Add your OPENAI_API_KEY to .env

# Run the web dashboard
cd prometheus_novel
python -m uvicorn interfaces.web.app:app --reload --port 8080

# Open: http://localhost:8080
```

---

## 🐳 Docker Deployment

**Best for:** Any cloud platform with Docker support

```bash
# Build
docker build -t writerai .

# Run
docker run -d -p 8080:8080 \
  -e OPENAI_API_KEY=your_key \
  writerai

# Access: http://localhost:8080
```

---

## 📚 Full Documentation

For detailed deployment instructions, see:

- **[DEPLOYMENT_COMPLETE_GUIDE.md](DEPLOYMENT_COMPLETE_GUIDE.md)** - Complete deployment options
- **[README.md](README.md)** - Project overview and features
- **[QUICKSTART.md](QUICKSTART.md)** - Get started quickly

---

## 🌐 GitHub Pages (Landing Page Only)

GitHub Pages will show the landing page at:
`https://yourusername.github.io/WriterAI/`

This page provides information and links but doesn't run the application.

**To enable:**
1. Go to repository Settings → Pages
2. Source: "Deploy from a branch"
3. Branch: "main", folder: "/ (root)"
4. Save

---

## ✅ What's Included

This repository includes everything you need:

- ✅ **Dockerfile** - For Docker deployments
- ✅ **requirements.txt** - Python dependencies
- ✅ **render.yaml** - Render.com configuration
- ✅ **Procfile** - Heroku configuration
- ✅ **fly.toml** - Fly.io configuration
- ✅ **railway.json** - Railway configuration
- ✅ **index.html** - Static landing page for GitHub Pages

---

## 🎨 What You Get After Deployment

### Web Dashboard (`/`)
- Beautiful UI for creating projects
- Browse 899 story ideas
- Manage novel projects
- Monitor generation progress

### API Documentation (`/api/v2/docs`)
- Interactive API explorer
- Complete REST API reference
- Test endpoints directly

### Health Check (`/api/v2/health`)
- System status
- Performance metrics
- Uptime monitoring

---

## 💡 Quick Tips

1. **API Key Security**: Never commit your `.env` file
2. **Cost Control**: Set spending limits in your OpenAI dashboard
3. **Free Tiers**: Render, Railway, and Fly.io offer free tiers
4. **Monitoring**: Check logs in your deployment platform dashboard

---

## 🐛 Troubleshooting

### "Application won't start"
- Check that `OPENAI_API_KEY` is set correctly
- Verify Python version is 3.10+
- Review logs in platform dashboard

### "Port already in use" (local)
```bash
# Kill process on port 8080
lsof -ti:8080 | xargs kill -9
```

### "Import errors"
```bash
# Reinstall dependencies
pip install -r requirements.txt
```

---

## 📞 Need Help?

- 📖 **[Full Documentation](DEPLOYMENT_COMPLETE_GUIDE.md)**
- 🐛 **[Report Issues](https://github.com/yourusername/WriterAI/issues)**
- 💬 **[Discussions](https://github.com/yourusername/WriterAI/discussions)**

---

**Ready to deploy? Start with Render for the easiest experience!**

🚀 **[Deploy to Render Now →](https://render.com)**

---

Made with ❤️ by the WriterAI Team

