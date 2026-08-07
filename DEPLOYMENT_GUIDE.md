# RackPulse Deployment Guide

## 🚀 Quick Deployment Steps

### 1. Vercel Configuration (Frontend)

**Environment Variables:**
- Set `VITE_API_BASE_URL` = `https://aquarack.onrender.com` in Vercel dashboard

**Automatic Deployment:**
- Push to GitHub → Vercel automatically deploys
- Current build: ✅ Successful (1.91s)
- Bundle size: 975 kB (285 kB gzipped)

### 2. Render Configuration (Backend)

**Already Deployed:**
- URL: https://aquarack.onrender.com
- Status: ✅ Working
- Database: CockroachDB Cloud connected

**Environment Variables Required:**
- `DATABASE_URL`: CockroachDB connection string
- `OLLAMA_BASE_URL`: Your Ollama instance URL
- `GROQ_API_KEY`: Groq API key
- `OPENAI_API_KEY`: OpenAI API key (optional)
- `COHERE_API_KEY`: Cohere API key (optional)

## 🔧 Configuration Files

### Frontend Files
- `.env.production` - Production API URL configuration
- `vercel.json` - SPA routing configuration
- `Dockerfile` - Multi-stage build (if needed)
- `nginx.conf` - Production nginx configuration

### Backend Files
- `render.yaml` - Render deployment configuration
- `Dockerfile` - Render-compatible Docker configuration
- `.env.aws.template` - AWS deployment template

## 📱 URLs

- **Frontend**: https://aqua-rack.vercel.app
- **Backend**: https://aquarack.onrender.com
- **Repository**: github.com/maria2469/AquaRack

## ✅ Pre-Deployment Checklist

### Frontend
- [x] All console logs removed
- [x] Production API URL configured
- [x] Missing API functions added
- [x] Build successful locally
- [x] Environment variables documented
- [x] SPA routing configured

### Backend
- [x] Dockerfile optimized for Render
- [x] Port configuration (8000)
- [x] Database connection configured
- [x] Health check endpoint available
- [x] All API endpoints tested

## 🧪 Testing

### Manual Testing
1. Visit https://aqua-rack.vercel.app
2. Test Fleet Management page
3. Verify RACK-004 appears as completed
4. Test "Run First 10 Racks" button
5. Check browser console for errors

### API Testing
```bash
# Test backend connectivity
curl https://aquarack.onrender.com/api/v1/fleet/summary
curl https://aquarack.onrender.com/api/v1/fleet/saved-results
```

## 🔒 Security

- ✅ No sensitive data in frontend code
- ✅ API keys via environment variables
- ✅ HTTPS only connections
- ✅ Device ID authentication
- ✅ CORS properly configured

## 📊 Performance

- **Frontend Build**: 1.91s
- **Bundle Size**: 975 kB (285 kB gzipped)
- **API Response**: ~200ms for summary endpoints
- **Database**: CockroachDB Cloud with SSL

## 🐛 Troubleshooting

### Common Issues

**1. Build Fails**
- Check for missing dependencies: `npm install`
- Verify all imports exist in `api.js`
- Check for TypeScript errors

**2. API Connection Issues**
- Verify `VITE_API_BASE_URL` is set in Vercel
- Check backend is running on Render
- Test backend endpoints directly

**3. SPA Routing Issues**
- Ensure `vercel.json` has rewrites configured
- Check for 404 errors on page refresh
- Verify client-side routing works

## 📝 Post-Deployment

1. **Monitor Logs**: Check Vercel and Render dashboards
2. **Test All Pages**: Ensure all routes work correctly
3. **Verify Data**: Check fleet data loads properly
4. **Performance**: Monitor bundle size and load times
5. **User Testing**: Test core user flows

## 🔄 Continuous Deployment

- **Automatic**: Push to GitHub → Both platforms deploy
- **Manual**: Can trigger deployments from dashboards
- **Rollback**: Both platforms support easy rollbacks

## 📞 Support

- **Vercel**: vercel.com/docs
- **Render**: render.com/docs
- **Repository**: github.com/maria2469/AquaRack