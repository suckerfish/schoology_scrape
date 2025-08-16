"""
Enhanced Summary page with centralized configuration and caching.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import sys
import os

# Add shared modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))

from config import get_config
from grade_data_service import create_grade_data_service

st.set_page_config(layout="wide", page_title="Grades Summary")


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
def get_latest_grades():
    """Get latest grades with caching."""
    service = get_data_service()
    if service:
        try:
            return service.get_latest_snapshot(use_cache=True)
        except Exception as e:
            st.error(f"Failed to load latest grades: {e}")
            return None
    return None


def create_summary_metrics(grades_data):
    """Create and display summary metrics."""
    if not grades_data:
        st.warning("No grade data available for metrics")
        return
    
    total_courses = len(grades_data)
    total_assignments = 0
    missing_assignments = 0
    not_graded = 0
    grade_values = []
    
    # Calculate metrics
    for course_data in grades_data.values():
        periods = course_data.get('periods', {})
        for period in periods.values():
            categories = period.get('categories', {})
            for category in categories.values():
                assignments = category.get('assignments', [])
                for assignment in assignments:
                    total_assignments += 1
                    grade = assignment.get('grade', 'N/A')
                    
                    if grade == 'Missing':
                        missing_assignments += 1
                    elif grade == 'Not graded':
                        not_graded += 1
                    else:
                        # Try to extract numeric grade
                        try:
                            if isinstance(grade, str) and '%' in grade:
                                numeric_grade = float(grade.replace('%', ''))
                                grade_values.append(numeric_grade)
                        except ValueError:
                            pass
    
    # Display metrics in columns
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Total Courses", total_courses)
    
    with col2:
        st.metric("Total Assignments", total_assignments)
    
    with col3:
        st.metric(
            "Missing Assignments", 
            missing_assignments, 
            delta=-missing_assignments if missing_assignments > 0 else None,
            delta_color="inverse"
        )
    
    with col4:
        st.metric("Not Graded", not_graded)
    
    with col5:
        if grade_values:
            avg_grade = sum(grade_values) / len(grade_values)
            st.metric("Average Grade", f"{avg_grade:.1f}%")
        else:
            st.metric("Average Grade", "N/A")


def create_course_cards(grades_data):
    """Create course overview cards."""
    if not grades_data:
        st.warning("No grade data available for course cards")
        return
    
    st.subheader("📚 Course Overview")
    
    # Create two columns per row
    for i in range(0, len(grades_data), 2):
        col1, col2 = st.columns(2)
        
        # First card in the row
        course_names = list(grades_data.keys())
        course_name = course_names[i]
        course_data = grades_data[course_name]
        
        with col1:
            with st.container(border=True):
                st.subheader(course_name)
                st.write(f"**Current Grade:** {course_data.get('course_grade', 'N/A')}")
                
                # Add period grades if they exist
                periods = course_data.get('periods', {})
                for period_name, period_data in periods.items():
                    period_grade = period_data.get('period_grade', 'N/A')
                    st.write(f"**{period_name}:** {period_grade}")
        
        # Second card in the row (if it exists)
        if i + 1 < len(course_names):
            course_name = course_names[i + 1]
            course_data = grades_data[course_name]
            
            with col2:
                with st.container(border=True):
                    st.subheader(course_name)
                    st.write(f"**Current Grade:** {course_data.get('course_grade', 'N/A')}")
                    
                    # Add period grades if they exist
                    periods = course_data.get('periods', {})
                    for period_name, period_data in periods.items():
                        period_grade = period_data.get('period_grade', 'N/A')
                        st.write(f"**{period_name}:** {period_grade}")


def create_missing_assignments_list(grades_data):
    """Create comprehensive missing assignments list."""
    if not grades_data:
        st.warning("No grade data available for missing assignments")
        return
    
    st.subheader("⚠️ Missing Assignments")
    
    missing_assignments = []
    for course_name, course_data in grades_data.items():
        periods = course_data.get('periods', {})
        for period_name, period_data in periods.items():
            categories = period_data.get('categories', {})
            for category_name, category_data in categories.items():
                assignments = category_data.get('assignments', [])
                for assignment in assignments:
                    if assignment.get('grade') == 'Missing':
                        missing_assignments.append({
                            'Course': course_name,
                            'Period': period_name,
                            'Category': category_name,
                            'Assignment': assignment.get('title', 'Unknown'),
                            'Due Date': assignment.get('due_date', 'No date')
                        })
    
    if missing_assignments:
        df = pd.DataFrame(missing_assignments)
        st.dataframe(df, hide_index=True, use_container_width=True)
        
        # Add download button
        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 Download Missing Assignments CSV",
            data=csv,
            file_name="missing_assignments.csv",
            mime="text/csv"
        )
    else:
        st.success("🎉 No missing assignments!")


def create_grade_distribution_chart(grades_data):
    """Create a grade distribution chart."""
    if not grades_data:
        return
    
    st.subheader("📊 Grade Distribution")
    
    grade_ranges = {'A (90-100%)': 0, 'B (80-89%)': 0, 'C (70-79%)': 0, 'D (60-69%)': 0, 'F (0-59%)': 0}
    
    for course_data in grades_data.values():
        periods = course_data.get('periods', {})
        for period in periods.values():
            categories = period.get('categories', {})
            for category in categories.values():
                assignments = category.get('assignments', [])
                for assignment in assignments:
                    grade = assignment.get('grade', 'N/A')
                    
                    try:
                        if isinstance(grade, str) and '%' in grade:
                            numeric_grade = float(grade.replace('%', ''))
                            if numeric_grade >= 90:
                                grade_ranges['A (90-100%)'] += 1
                            elif numeric_grade >= 80:
                                grade_ranges['B (80-89%)'] += 1
                            elif numeric_grade >= 70:
                                grade_ranges['C (70-79%)'] += 1
                            elif numeric_grade >= 60:
                                grade_ranges['D (60-69%)'] += 1
                            else:
                                grade_ranges['F (0-59%)'] += 1
                    except ValueError:
                        pass
    
    if any(grade_ranges.values()):
        df_grades = pd.DataFrame(list(grade_ranges.items()), columns=['Grade Range', 'Count'])
        fig = px.bar(df_grades, x='Grade Range', y='Count', 
                    title='Assignment Grade Distribution',
                    color='Count',
                    color_continuous_scale='RdYlGn')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No gradeable assignments found for distribution chart")


def main():
    """Main summary page function."""
    st.title('📋 Grades Summary')
    
    try:
        grades_data = get_latest_grades()
        if not grades_data:
            st.error('📭 No grades data available')
            st.info("Make sure the scraper has run at least once and data is stored in the database.")
            return
        
        # Create summary metrics at the top
        create_summary_metrics(grades_data)
        
        st.divider()
        
        # Create course cards
        create_course_cards(grades_data)
        
        st.divider()
        
        # Create grade distribution chart
        create_grade_distribution_chart(grades_data)
        
        st.divider()
        
        # Create missing assignments list
        create_missing_assignments_list(grades_data)
        
    except Exception as e:
        st.error(f"Error loading summary data: {e}")


if __name__ == "__main__":
    main()