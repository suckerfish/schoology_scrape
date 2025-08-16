# Core Architecture Adjustments Plan

Based on analysis of the current Schoology Grade Scraper codebase, here are the main architectural improvements recommended:

## Current Architecture Analysis

### Coupling Issues Identified:
- **Tight Coupling**: Streamlit viewer directly imports `dynamodb_manager.py`
- **Scattered Dependencies**: DynamoDB calls across 6 files (`main.py`, `streamlit_viewer.py`, all 4 page files)
- **Monolithic Main**: `main.py` handles scraping, comparison, storage, and notifications
- **Configuration Sprawl**: Environment variables accessed directly in multiple modules

## 1. **Decouple Streamlit Viewer from Scraper** ✅ (Primary suggestion)

**Problem**: Currently tight coupling through shared `dynamodb_manager.py` and direct imports

**Solution**: Create separate deployable packages:
- `schoology-scraper/` - Standalone scraping service  
- `schoology-dashboard/` - Independent Streamlit app
- Shared data contract via DynamoDB (already exists)

**Benefits**:
- Independent deployment and scaling
- Separate development cycles
- Easier testing and maintenance
- Clear separation of concerns

## 2. **Service Layer Abstraction**

**Problem**: Direct DynamoDB calls scattered across 6 files

**Solution**: Create `GradeDataService` interface to:
- Abstract data access from storage implementation
- Enable easier testing and future storage changes
- Centralize data transformation logic

**Example Interface**:
```python
class GradeDataService:
    def get_latest_snapshot() -> dict
    def get_all_snapshots() -> list
    def get_snapshot_by_date(date: str) -> dict
    def save_snapshot(data: dict) -> str
```

## 3. **Configuration Management**

**Problem**: Environment variables scattered across modules

**Solution**: Centralized `config.py` with:
- Validation and defaults
- Environment-specific configs
- Single source of truth for all settings

**Structure**:
```python
@dataclass
class Config:
    # Schoology credentials
    google_email: str
    google_password: str
    
    # AWS settings
    aws_key: str
    aws_secret: str
    
    # Notification settings
    pushover_token: str
    gemini_key: str
```

## 4. **Notification Service Decoupling**

**Problem**: `main.py` directly imports 3 notification modules (`pushover.py`, `email_myself.py`, `gemini_client.py`)

**Solution**: Plugin-based notification system:
- Abstract `NotificationProvider` interface
- Dynamic loading of notification plugins
- Easier to add/remove notification channels

**Benefits**:
- Pluggable notification system
- Easier testing (mock notifications)
- Runtime configuration of notification channels

## 5. **Data Pipeline Separation**

**Problem**: Single `main.py` handles scraping, comparison, storage, and notifications

**Solution**: Split into focused modules:
- `scraper.py` - Pure data extraction
- `comparator.py` - Change detection logic using DeepDiff
- `pipeline.py` - Orchestration and workflow
- `notifier.py` - Alert coordination

**Pipeline Flow**:
```
scraper.py → comparator.py → storage → notifier.py
```

## Implementation Priority

### ~~**Phase 1: Viewer Decoupling**~~ ✅ **COMPLETED**
1. ~~Extract Streamlit app to separate directory~~ ✅
2. ~~Create shared data service interface~~ ✅
3. ~~Update import dependencies~~ ✅
4. ~~Test independent deployment~~ ✅

### **Phase 2: Service Layer** (Short-term)
1. Implement `GradeDataService` abstraction
2. Centralize configuration management
3. Refactor all modules to use services

### **Phase 3: Pipeline Refactoring** (Medium-term)
1. Split notification system into plugins
2. Separate data pipeline concerns
3. Add comprehensive error handling and retry logic

## Additional Considerations

### **Current Strengths to Preserve**:
- ✅ Standard Selenium WebDriver (recently migrated from undetected-chromedriver)
- ✅ DynamoDB for historical tracking
- ✅ DeepDiff for accurate change detection
- ✅ Multi-page Streamlit dashboard
- ✅ Hierarchical data structure

### **Technical Debt to Address**:
- Remove `undetected-chromedriver==3.5.4` from requirements.txt (no longer used)
- Add comprehensive error handling
- Implement retry logic for web scraping
- Add caching to Streamlit pages
- Replace DynamoDB table scans with optimized queries

## Benefits of This Architecture

1. **Modularity**: Clear separation of concerns
2. **Testability**: Each component can be tested independently
3. **Scalability**: Components can be scaled independently
4. **Maintainability**: Easier to modify individual parts
5. **Deployability**: Separate deployment of scraper vs dashboard
6. **Flexibility**: Easy to swap storage backends or notification providers

This plan maintains all current functionality while enabling independent deployment, better testing, and future scaling opportunities.