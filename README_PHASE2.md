# Phase 2 Quick Start Guide

## 🚀 What's New in Phase 2

Phase 2 eliminates "configuration sprawl" and adds intelligent caching, data validation, and error handling.

## ✅ What's Actually Working Now

### **Enhanced Components (Ready to Use):**
- **Enhanced Scraper**: `schoology-scraper/main_enhanced.py`
- **Enhanced Dashboard**: `schoology-dashboard/streamlit_viewer_enhanced.py`
- **Centralized Config**: `shared/config.py`
- **Data Validation**: Blocks corrupt data automatically
- **Intelligent Caching**: Faster dashboard performance

## 🔧 How to Use Phase 2

### **Option 1: Use Enhanced Scraper**
```bash
cd schoology-scraper
python main_enhanced.py  # Instead of main.py
```
**Benefits:** Centralized config, data validation, better error handling

### **Option 2: Use Enhanced Dashboard**
```bash
cd schoology-dashboard
streamlit run streamlit_viewer_enhanced.py  # Instead of streamlit_viewer.py
```
**Benefits:** Faster loading with caching, better error messages

### **Option 3: Use Both Enhanced (Recommended)**
```bash
# For scraping:
cd schoology-scraper && python main_enhanced.py

# For viewing:  
cd schoology-dashboard && streamlit run streamlit_viewer_enhanced.py
```

## 📱 Optional: Enable Notifications

If you want phone notifications when grades change:

1. **Get Pushover account**: Sign up at pushover.net
2. **Add tokens to .env**:
   ```
   pushover_token=your_app_token
   pushover_userkey=your_user_key
   ```
3. **Install Pushover app** on your phone

The enhanced scraper will automatically send notifications when it detects changes.

## 🛡️ Data Protection

The enhanced version automatically:
- ✅ **Validates data** before saving
- ✅ **Blocks corrupt data** from entering database  
- ✅ **Creates backup files** when validation fails
- ✅ **Sends error alerts** when problems occur

Your historical data is now protected from website scraping issues.

## 🎯 Key Differences

| Old Version | Enhanced Version |
|---|---|
| Settings scattered across files | Single config.py |
| No data validation | Blocks corrupt data |
| No caching | Intelligent caching |
| Basic error handling | Comprehensive retry logic |
| Manual dashboard checking | Optional push notifications |

## 🔄 Fallback

If you have issues with enhanced versions:
- **Scraper**: Use original `main.py`
- **Dashboard**: Use original `streamlit_viewer.py`

All Phase 1 decoupling improvements still work in both versions.

## 📋 Next Steps

1. **Try enhanced scraper**: `python main_enhanced.py`
2. **Try enhanced dashboard**: `streamlit run streamlit_viewer_enhanced.py`
3. **Set up notifications** (optional)
4. **Set up cron job** for automation (optional)

Phase 2 is production-ready and maintains full compatibility with your existing data!