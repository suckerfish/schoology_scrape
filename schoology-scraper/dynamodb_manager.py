import boto3
from datetime import datetime
from dotenv import load_dotenv
import os

class DynamoDBManager:
    def __init__(self):
        load_dotenv()
        self.aws_key = os.getenv('aws_key')
        self.aws_secret = os.getenv('aws_secret')
        self.table_name = 'SchoologyGrades'
        
        self.dynamodb = boto3.resource(
            'dynamodb',
            aws_access_key_id=self.aws_key,
            aws_secret_access_key=self.aws_secret,
            region_name='us-west-1'
        )
        self.table = self.dynamodb.Table(self.table_name)
    
    def add_entry(self, data):
        timestamp = datetime.now().replace(microsecond=0).isoformat()
        item = {
            'Date': timestamp,  # partition key
            'Data': data
        }
        self.table.put_item(Item=item)
        print(f"Successfully wrote entry to DynamoDB with timestamp: {timestamp}")
        return timestamp
    
    def read_entry(self, timestamp):
        response = self.table.get_item(
            Key={
                'Date': timestamp
            }
        )
        return response.get('Item')

if __name__ == '__main__':
    db = DynamoDBManager()
    
    # Get user input
    print("Enter grade data:")
    data = input("> ")
    
    # Add entry
    timestamp = db.add_entry(data)
    
    # Confirm and read back
    print("\nEntry added. Reading back data...")
    entry = db.read_entry(timestamp)
    print(f"Date: {entry['Date']}")
    print(f"Data: {entry['Data']}") 