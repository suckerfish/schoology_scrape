import streamlit as st
st.set_page_config(layout="centered")
st.markdown("""
    <style>
        .block-container {
            max-width: 1000px;  # Default is around 730px
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
    </style>
""", unsafe_allow_html=True)
from dynamodb_manager import DynamoDBManager
from datetime import datetime, timedelta
import pandas as pd

def get_latest_grades():
    db = DynamoDBManager()
    response = db.table.scan(
        ProjectionExpression='#date, #data',
        ExpressionAttributeNames={
            '#date': 'Date',
            '#data': 'Data'
        }
    )
    items = response.get('Items', [])
    if not items:
        return None
    
    return sorted(items, key=lambda x: x['Date'], reverse=True)[0]['Data']

def display_grades_tree(grades_data):
    for course_name, course_data in grades_data.items():
        with st.expander(f"{course_name} ({course_data['course_grade']})"):
            # Sort periods by name, which will put T1 before T2
            sorted_periods = sorted(course_data['periods'].items())
            for period_name, period_data in sorted_periods:
                st.subheader(f"{period_name} - {period_data['period_grade']}")
                
                for category_name, category_data in period_data['categories'].items():
                    st.write(f"**{category_name} - {category_data['category_grade']}**")
                    
                    # Create a DataFrame for assignments in this category
                    assignments = category_data['assignments']
                    if assignments:
                        df = pd.DataFrame(
                            [[a['title'], a['grade']] for a in assignments],
                            columns=['Assignment', 'Grade']
                        )
                        st.dataframe(df, hide_index=True)
                st.divider()

def main():
    st.title('Schoology Grades')
    
    grades_data = get_latest_grades()
    if not grades_data:
        st.error('No recent grades data available')
        return
    
    display_grades_tree(grades_data)

if __name__ == "__main__":
    main() 