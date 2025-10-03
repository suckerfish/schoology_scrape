import streamlit as st
import pandas as pd
from shared.local_snapshots import get_latest_snapshots

st.set_page_config(layout="wide", page_title="Assignment List")

def load_latest_snapshots(count=2):
    # New: read the latest N snapshots from local files
    return get_latest_snapshots(count=count)

def extract_assignments(data):
    assignments = []
    for course_name, course_data in data.items():
        for period_name, period_data in course_data['periods'].items():
            for category_name, category_data in period_data['categories'].items():
                for assignment in category_data['assignments']:
                    assignments.append({
                        'Course': course_name,
                        'Period': period_name,
                        'Category': category_name,
                        'Assignment': assignment['title'],
                        'Grade': assignment['grade'],
                        'Due Date': assignment.get('due_date', 'N/A'),
                        'Notes': assignment.get('comment', '')
                    })
    return pd.DataFrame(assignments)

def identify_new_assignments(current_df, previous_df):
    if previous_df is None or previous_df.empty:
        return current_df['Assignment'].map(lambda x: True)
    
    return ~current_df['Assignment'].isin(previous_df['Assignment'])

def main():
    st.title('Assignment List')
    
    # Get latest two snapshots
    snapshots = load_latest_snapshots(2)
    if not snapshots:
        st.error('No assignment data available')
        return
    
    current_data = extract_assignments(snapshots[0]['Data'])
    previous_data = extract_assignments(snapshots[1]['Data']) if len(snapshots) > 1 else None
    
    # Identify new assignments
    is_new = identify_new_assignments(current_data, previous_data)
    
    # Display assignments with highlighting
    st.dataframe(
        current_data.style.apply(
            lambda x: ['background-color: #ffcdd2' if is_new[i] else '' 
                      for i in range(len(x))], axis=0
        ),
        use_container_width=True
    )

    # Summary statistics
    st.sidebar.header('Summary')
    st.sidebar.metric('Total Assignments', len(current_data))
    st.sidebar.metric('New Assignments', sum(is_new))
    
    # Filter options
    st.sidebar.header('Filters')
    selected_course = st.sidebar.multiselect(
        'Select Courses',
        options=current_data['Course'].unique()
    )
    
    if selected_course:
        filtered_data = current_data[current_data['Course'].isin(selected_course)]
        st.header('Filtered Assignments')
        st.dataframe(
            filtered_data.style.apply(
                lambda x: ['background-color: #ffcdd2' if is_new[current_data.index[i]] else '' 
                          for i in range(len(x))], axis=0
            ),
            use_container_width=True
        )

if __name__ == "__main__":
    main() 
