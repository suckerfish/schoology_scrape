import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))
from grade_data_service import create_grade_data_service
from datetime import datetime

st.set_page_config(layout="wide", page_title="Grade Analytics")

def get_all_snapshots():
    service = create_grade_data_service()
    snapshots = service.get_all_snapshots()
    # Return sorted by date (oldest first for trends)
    return sorted(snapshots, key=lambda x: x['Date'])

def extract_numeric_grade(grade_str):
    try:
        return float(grade_str.rstrip('%'))
    except (ValueError, AttributeError):
        return None

def prepare_trend_data(snapshots):
    trend_data = []
    for snapshot in snapshots:
        date = datetime.fromisoformat(snapshot['Date'])
        for course_name, course_data in snapshot['Data'].items():
            grade = extract_numeric_grade(course_data['course_grade'])
            if grade is not None:
                trend_data.append({
                    'Date': date,
                    'Course': course_name,
                    'Grade': grade
                })
    return pd.DataFrame(trend_data)

def create_grade_distribution(latest_data):
    grades = []
    for course_name, course_data in latest_data.items():
        for period_name, period_data in course_data['periods'].items():
            for category_name, category_data in period_data['categories'].items():
                for assignment in category_data['assignments']:
                    grade = extract_numeric_grade(assignment['grade'])
                    if grade is not None:
                        grades.append({
                            'Course': course_name,
                            'Assignment': assignment['title'],
                            'Grade': grade
                        })
    return pd.DataFrame(grades)

def main():
    st.title('Grade Analytics')
    
    snapshots = get_all_snapshots()
    if not snapshots:
        st.error('No grades data available')
        return
    
    # Grade Trends Over Time
    st.header('Grade Trends')
    trend_data = prepare_trend_data(snapshots)
    if not trend_data.empty:
        fig = px.line(trend_data, x='Date', y='Grade', color='Course',
                     title='Grade Progression Over Time',
                     labels={'Grade': 'Grade (%)', 'Date': 'Date'})
        st.plotly_chart(fig, use_container_width=True)
    
    # Latest Grade Distribution
    st.header('Grade Distribution')
    latest_data = snapshots[-1]['Data']
    dist_data = create_grade_distribution(latest_data)
    if not dist_data.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            fig_hist = px.histogram(dist_data, x='Grade', 
                                  title='Overall Grade Distribution',
                                  nbins=20)
            st.plotly_chart(fig_hist, use_container_width=True)
        
        with col2:
            fig_box = px.box(dist_data, x='Course', y='Grade',
                           title='Grade Distribution by Course')
            fig_box.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig_box, use_container_width=True)
    
    # Course Performance Summary
    st.header('Course Performance Summary')
    latest_grades = []
    for course, data in latest_data.items():
        grade = extract_numeric_grade(data['course_grade'])
        if grade is not None:
            latest_grades.append({'Course': course, 'Grade': grade})
    
    if latest_grades:
        df_summary = pd.DataFrame(latest_grades)
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=df_summary['Grade'].mean(),
            title={'text': "Overall Average"},
            gauge={'axis': {'range': [0, 100]},
                  'bar': {'color': "darkblue"},
                  'steps': [
                      {'range': [0, 60], 'color': "red"},
                      {'range': [60, 70], 'color': "orange"},
                      {'range': [70, 80], 'color': "yellow"},
                      {'range': [80, 90], 'color': "lightgreen"},
                      {'range': [90, 100], 'color': "green"}
                  ]}))
        st.plotly_chart(fig_gauge, use_container_width=True)

if __name__ == "__main__":
    main() 