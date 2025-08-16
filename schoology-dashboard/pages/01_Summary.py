import streamlit as st
import pandas as pd
import plotly.express as px
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))
from grade_data_service import create_grade_data_service

st.set_page_config(layout="wide", page_title="Grades Summary")

def get_latest_grades():
    service = create_grade_data_service()
    return service.get_latest_snapshot()

def create_summary_metrics(grades_data):
    total_courses = len(grades_data)
    total_assignments = 0
    missing_assignments = 0
    not_graded = 0
    
    # Calculate metrics
    for course_data in grades_data.values():
        for period in course_data['periods'].values():
            for category in period['categories'].values():
                for assignment in category['assignments']:
                    total_assignments += 1
                    if assignment['grade'] == 'Missing':
                        missing_assignments += 1
                    elif assignment['grade'] == 'Not graded':
                        not_graded += 1
    
    # Display metrics in columns
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Courses", total_courses)
    with col2:
        st.metric("Total Assignments", total_assignments)
    with col3:
        st.metric("Missing Assignments", missing_assignments, 
                 delta=-missing_assignments, delta_color="inverse")
    with col4:
        st.metric("Not Graded", not_graded)

def create_course_cards(grades_data):
    st.subheader("Course Overview")
    
    # Create two columns per row
    for i in range(0, len(grades_data), 2):
        col1, col2 = st.columns(2)
        
        # First card in the row
        course_name = list(grades_data.keys())[i]
        course_data = grades_data[course_name]
        with col1:
            with st.container(border=True):
                st.subheader(course_name)
                st.write(f"Current Grade: {course_data['course_grade']}")
                
                # Add period grades if they exist
                for period_name, period_data in course_data['periods'].items():
                    st.write(f"{period_name}: {period_data['period_grade']}")
        
        # Second card in the row (if it exists)
        if i + 1 < len(grades_data):
            course_name = list(grades_data.keys())[i + 1]
            course_data = grades_data[course_name]
            with col2:
                with st.container(border=True):
                    st.subheader(course_name)
                    st.write(f"Current Grade: {course_data['course_grade']}")
                    
                    # Add period grades if they exist
                    for period_name, period_data in course_data['periods'].items():
                        st.write(f"{period_name}: {period_data['period_grade']}")

def create_missing_assignments_list(grades_data):
    st.subheader("Missing Assignments")
    
    missing_assignments = []
    for course_name, course_data in grades_data.items():
        for period_name, period_data in course_data['periods'].items():
            for category_name, category_data in period_data['categories'].items():
                for assignment in category_data['assignments']:
                    if assignment['grade'] == 'Missing':
                        missing_assignments.append({
                            'Course': course_name,
                            'Period': period_name,
                            'Category': category_name,
                            'Assignment': assignment['title'],
                            'Due Date': assignment.get('due_date', 'No date')
                        })
    
    if missing_assignments:
        df = pd.DataFrame(missing_assignments)
        st.dataframe(df, hide_index=True)
    else:
        st.success("No missing assignments! 🎉")

def main():
    st.title('Grades Summary')
    
    grades_data = get_latest_grades()
    if not grades_data:
        st.error('No grades data available')
        return
    
    # Create summary metrics at the top
    create_summary_metrics(grades_data)
    
    # Add a divider
    st.divider()
    
    # Create course cards
    create_course_cards(grades_data)
    
    # Add a divider
    st.divider()
    
    # Create missing assignments list
    create_missing_assignments_list(grades_data)

if __name__ == "__main__":
    main()
