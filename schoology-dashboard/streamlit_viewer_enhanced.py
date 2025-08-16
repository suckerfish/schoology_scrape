"""
Enhanced Streamlit dashboard with centralized configuration and improved data service.
This version uses the Phase 2 architectural improvements.
"""
import streamlit as st
import sys
import os
import pandas as pd
import logging
from datetime import datetime
from deepdiff import DeepDiff

# Add shared modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'shared'))

from config import get_config, setup_logging
from grade_data_service import create_grade_data_service

# Configure Streamlit page
st.set_page_config(
    layout="centered", 
    page_title="Schoology Grades Dashboard",
    page_icon="📊"
)

# Custom CSS
st.markdown("""
    <style>
        .block-container {
            max-width: 1000px;  # Default is around 730px
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        .streamlit-expanderHeader {
            font-weight: bold;
            background-color: #f0f2f6;
        }
        .stDataFrame {
            width: 100% !important;
        }
        .metric-container {
            background-color: #f0f2f6;
            padding: 1rem;
            border-radius: 0.5rem;
            margin: 0.5rem 0;
        }
    </style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_data_service():
    """Get configured data service instance."""
    try:
        config = get_config()
        return create_grade_data_service(enhanced=True, config=config)
    except Exception as e:
        st.error(f"Failed to initialize data service: {e}")
        return None


@st.cache_data(ttl=60)  # Cache for 1 minute
def get_all_snapshots():
    """Get all snapshots with caching."""
    service = get_data_service()
    if service:
        try:
            return service.get_all_snapshots(use_cache=True)
        except Exception as e:
            st.error(f"Failed to load snapshots: {e}")
            return []
    return []


@st.cache_data(ttl=60)
def get_summary_stats():
    """Get summary statistics with caching."""
    service = get_data_service()
    if service:
        try:
            return service.get_summary_stats()
        except Exception as e:
            st.error(f"Failed to load summary stats: {e}")
            return None
    return None


def format_snapshot_label(snapshot):
    """Convert ISO format to readable timestamp."""
    try:
        date = datetime.fromisoformat(snapshot['Date'])
        return date.strftime('%b %d, %Y at %H:%M')
    except Exception:
        return snapshot['Date']


def display_dashboard_header():
    """Display the dashboard header with stats."""
    st.title('📊 Schoology Grades Dashboard')
    
    # Display summary stats
    stats = get_summary_stats()
    if stats:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Snapshots", stats['total_snapshots'])
        
        with col2:
            if stats['latest_snapshot_date']:
                latest_date = datetime.fromisoformat(stats['latest_snapshot_date'])
                st.metric("Latest Update", latest_date.strftime('%m/%d %H:%M'))
        
        with col3:
            if stats.get('cache_stats'):
                st.metric("Cache Entries", stats['cache_stats']['cache_entries'])
        
        with col4:
            if stats.get('cache_stats'):
                st.metric("Cache TTL", f"{stats['cache_stats']['cache_ttl_seconds']}s")


def display_grades_tree(grades_data):
    """Display the hierarchical grades tree."""
    if not grades_data:
        st.warning("No grade data available")
        return
    
    for course_name, course_data in grades_data.items():
        with st.expander(f"{course_name} ({course_data.get('course_grade', 'N/A')})", expanded=False):
            periods = course_data.get('periods', {})
            
            if not periods:
                st.info("No period data available for this course")
                continue
            
            # Sort periods by name
            sorted_periods = sorted(periods.items())
            
            # Create tabs for each period
            if len(sorted_periods) > 1:
                period_tabs = st.tabs([f"{period_name} - {period_data.get('period_grade', 'N/A')}" 
                                     for period_name, period_data in sorted_periods])
                
                # Fill each tab with its content
                for tab, (period_name, period_data) in zip(period_tabs, sorted_periods):
                    with tab:
                        display_period_content(period_data)
            else:
                # Single period - no tabs needed
                period_name, period_data = sorted_periods[0]
                st.subheader(f"{period_name} - {period_data.get('period_grade', 'N/A')}")
                display_period_content(period_data)


def display_period_content(period_data):
    """Display content for a single period."""
    categories = period_data.get('categories', {})
    
    if not categories:
        st.info("No category data available for this period")
        return
    
    for category_name, category_data in categories.items():
        st.write(f"**{category_name} - {category_data.get('category_grade', 'N/A')}**")
        
        # Create a DataFrame for assignments in this category
        assignments = category_data.get('assignments', [])
        if assignments:
            df_data = []
            for assignment in assignments:
                df_data.append([
                    assignment.get('title', 'Unknown'),
                    assignment.get('due_date', ''),
                    assignment.get('grade', 'N/A')
                ])
            
            df = pd.DataFrame(df_data, columns=['Assignment', 'Due Date', 'Grade'])
            st.table(df.set_index('Assignment'))
        else:
            st.info("No assignments in this category")
    
    st.divider()


def display_grade_changes(current_data, previous_data):
    """Display changes between snapshots."""
    st.header("📈 Changes from Previous Snapshot")
    
    if not previous_data:
        st.info("No previous snapshot available for comparison")
        return
    
    # Add debug toggle
    debug_mode = st.checkbox("Show debug information", value=False)
    
    if debug_mode:
        st.write("**Debug Information:**")
        st.write(f"Current snapshot date: {list(current_data.keys())[0] if current_data else 'None'}")
        st.write(f"Previous snapshot date: {list(previous_data.keys())[0] if previous_data else 'None'}")
    
    changes_found = False
    
    # Compare course by course
    for course_name, current_course in current_data.items():
        course_changes = []
        
        # Check course grade changes
        if course_name in previous_data:
            prev_course = previous_data[course_name]
            
            # Course grade comparison
            current_grade = current_course.get('course_grade', 'N/A')
            prev_grade = prev_course.get('course_grade', 'N/A')
            if current_grade != prev_grade:
                course_changes.append(f"Course grade changed from {prev_grade} to {current_grade}")
            
            # Check each period
            current_periods = current_course.get('periods', {})
            prev_periods = prev_course.get('periods', {})
            
            for period_name, current_period in current_periods.items():
                if period_name in prev_periods:
                    prev_period = prev_periods[period_name]
                    
                    # Period grade comparison
                    current_period_grade = current_period.get('period_grade', 'N/A')
                    prev_period_grade = prev_period.get('period_grade', 'N/A')
                    if current_period_grade != prev_period_grade:
                        course_changes.append(f"{period_name} grade changed from {prev_period_grade} to {current_period_grade}")
                    
                    # Check assignments in each category
                    current_categories = current_period.get('categories', {})
                    prev_categories = prev_period.get('categories', {})
                    
                    for cat_name, current_cat in current_categories.items():
                        if cat_name in prev_categories:
                            prev_cat = prev_categories[cat_name]
                            
                            # Compare assignments
                            current_assignments = {a.get('title', 'Unknown'): a for a in current_cat.get('assignments', [])}
                            prev_assignments = {a.get('title', 'Unknown'): a for a in prev_cat.get('assignments', [])}
                            
                            # Check for new or changed assignments
                            for title, current_assignment in current_assignments.items():
                                if title not in prev_assignments:
                                    grade = current_assignment.get('grade', 'N/A')
                                    course_changes.append(f"New assignment in {cat_name}: {title} ({grade})")
                                else:
                                    prev_assignment = prev_assignments[title]
                                    current_grade = current_assignment.get('grade', 'N/A')
                                    prev_grade = prev_assignment.get('grade', 'N/A')
                                    
                                    if current_grade != prev_grade:
                                        course_changes.append(f"In {cat_name}, {title} grade changed from {prev_grade} to {current_grade}")
                                    
                                    # Check for comment changes
                                    current_comment = current_assignment.get('comment', '')
                                    prev_comment = prev_assignment.get('comment', '')
                                    if current_comment != prev_comment and current_comment:
                                        course_changes.append(f"New comment on {title}: {current_comment}")
        else:
            # New course added
            course_changes.append("New course added")
        
        # Display changes for this course if any were found
        if course_changes:
            changes_found = True
            with st.expander(f"🔄 Changes in {course_name}", expanded=True):
                for change in course_changes:
                    st.write(f"• {change}")
    
    if not changes_found:
        st.success("✅ No changes detected between snapshots")


def main():
    """Main dashboard function."""
    try:
        # Display header
        display_dashboard_header()
        
        # Get all snapshots
        snapshots = get_all_snapshots()
        if not snapshots:
            st.error('📭 No grades data available')
            st.info("Make sure the scraper has run at least once and data is stored in DynamoDB.")
            return
        
        # Create list of snapshot labels
        snapshot_labels = [format_snapshot_label(snapshot) for snapshot in snapshots]
        
        # Snapshot selector
        st.subheader("📅 Select Snapshot")
        selected_label = st.selectbox(
            'Choose a snapshot to view:',
            snapshot_labels,
            index=0,  # Default to most recent
            help="Select a snapshot to view grades data from that point in time"
        )
        
        # Find the selected snapshot
        selected_index = snapshot_labels.index(selected_label)
        selected_snapshot = snapshots[selected_index]
        
        # Display timestamp of selected snapshot
        st.caption(f"📊 Viewing grades as of **{selected_label}**")
        
        # Display the grades for the selected snapshot
        st.subheader("🎓 Course Grades")
        display_grades_tree(selected_snapshot.get('Data', {}))
        
        # Get previous snapshot for comparison
        if selected_index + 1 < len(snapshots):
            previous_snapshot = snapshots[selected_index + 1]
            st.divider()
            display_grade_changes(
                selected_snapshot.get('Data', {}), 
                previous_snapshot.get('Data', {})
            )
        
        # Display cache information
        with st.expander("ℹ️ System Information", expanded=False):
            stats = get_summary_stats()
            if stats:
                st.json(stats)
    
    except Exception as e:
        st.error(f"Dashboard error: {e}")
        logging.error(f"Dashboard error: {e}")


if __name__ == "__main__":
    main()