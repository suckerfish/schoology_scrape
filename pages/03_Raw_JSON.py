import streamlit as st
from datetime import datetime
from shared.local_snapshots import get_all_snapshots

def load_all_snapshots():
    # New: read from local files
    return get_all_snapshots()

def format_snapshot_label(snapshot):
    # Convert ISO format to datetime
    date = datetime.fromisoformat(snapshot['Date'])
    # Format as "Feb 15, 2024 at 14:30"
    return date.strftime('%b %d, %Y at %H:%M')

def main():
    st.title('Raw Grade Data (JSON)')
    
    # Get all snapshots
    snapshots = load_all_snapshots()
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
    
    # Display the raw JSON data
    st.json(selected_snapshot['Data'])

if __name__ == "__main__":
    main()
