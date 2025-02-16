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

def get_all_snapshots():
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
        return []
    
    # Sort items by date, newest first
    return sorted(items, key=lambda x: x['Date'], reverse=True)

def format_snapshot_label(snapshot):
    # Convert ISO format to datetime
    date = datetime.fromisoformat(snapshot['Date'])
    # Format as "Feb 15, 2024 at 14:30"
    return date.strftime('%b %d, %Y at %H:%M')

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
    
    # Get all snapshots
    snapshots = get_all_snapshots()
    if not snapshots:
        st.error('No grades data available')
        return
    
    # Create list of snapshot labels
    snapshot_labels = [format_snapshot_label(snapshot) for snapshot in snapshots]
    
    # Add snapshot selector with the most recent as default
    selected_label = st.selectbox(
        'Select Snapshot',
        snapshot_labels,
        index=0  # Default to most recent
    )
    
    # Find the selected snapshot
    selected_index = snapshot_labels.index(selected_label)
    selected_snapshot = snapshots[selected_index]
    
    # Display timestamp of selected snapshot
    st.caption(f"Viewing grades as of {selected_label}")
    
    # Display the grades for the selected snapshot
    display_grades_tree(selected_snapshot['Data'])

if __name__ == "__main__":
    main()