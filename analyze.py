import csv
import hashlib
import json
import sqlite3
from lxml import etree
from llama import analyze_sms
import typer
from loguru import logger
import datetime
from tqdm import tqdm
from typing import Dict, List, Optional

app = typer.Typer()

def remove_newlines_non_ascii(text: str) -> str:
    """Clean text by removing newlines and non-ASCII characters."""
    # also remove any non-printable characters, quotation marks, and other special characters
    return text.replace('\n', ' ').encode('ascii', 'ignore').decode('ascii').replace('"', '').replace("'", '')

def json_to_string(json_obj: Dict) -> str:
    """Convert JSON object to string."""
    return json.dumps(json_obj)

def floatify(value: str) -> float:
    """Convert string to float."""
    try:
        return float(value)
    except ValueError:
        return 0.0

def parse_sms_xml(xml_file: str) -> List[Dict]:
    """Parse XML file containing SMS data with improved error handling."""
    try:
        with open(xml_file, 'r', encoding='utf-8') as file:
            xml_string = file.read()
        
        root = etree.fromstring(xml_string.encode('utf-8'))
        sms_list = []
        
        for sms in root.xpath('//sms'):
            sms_dict = dict(sms.attrib)
            
            # Convert timestamp
            if 'date' in sms_dict:
                try:
                    timestamp = int(sms_dict['date'])
                    sms_dict['date'] = datetime.datetime.fromtimestamp(
                        timestamp / 1000
                    ).strftime('%Y-%m-%d %H:%M:%S')
                except (ValueError, TypeError):
                    logger.warning(f"Invalid date format: {sms_dict.get('date')}")
                    sms_dict['date'] = None
            
            # Clean and normalize phone numbers
            if 'address' in sms_dict:
                sms_dict['address'] = str(sms_dict['address']).strip()
            
            # Clean message body
            if 'body' in sms_dict:
                sms_dict['body'] = remove_newlines_non_ascii(sms_dict['body'])
                sms_dict['body_md5'] = hashlib.md5(
                    sms_dict['body'].encode()
                ).hexdigest()
            
            sms_list.append(sms_dict)
        
        return sms_list
    
    except Exception as e:
        logger.error(f"Error parsing XML file: {e}")
        raise

def analyze_sms_list(sms_list: List[Dict]) -> List[Dict]:
    """Analyze SMS messages with improved data handling and validation."""
    output = []
    for sms in tqdm(sms_list, desc="Analyzing SMS"):
        if not sms.get('body'):
            continue
            
        # Analyze message content
        try:
            content, json_analysis = analyze_sms(sms['body'])
        
        
            # Prepare analysis result
            analysis_result = {
                'date': sms.get('date'),
                'source': sms.get('address'),
                'body': sms.get('body'),
                'body_md5': sms.get('body_md5'),
                'llm_output': json_to_string(json_analysis),
                
                # Extract specific fields from LLM analysis
                'amount': floatify(json_analysis.get('Amount', 0)) if json_analysis else 0,
                'type': json_analysis.get('Type', 'Unknown'),
                'transaction_source': json_analysis.get('Source'),
                'destination': json_analysis.get('Destination'),
                'category': json_analysis.get('Category', 'Unknown'),
            }
        except Exception as e:
            logger.error(f"Error analyzing SMS: {e}")
            continue
        
        output.append(analysis_result)
    
    return output

def ensure_keys(json_obj: Dict) -> Dict:
    """Ensure all required keys exist with appropriate defaults."""
    defaults = {
        'date': None,
        'source': '',
        'destination': '',
        'body': '',
        'body_md5': '',
        'llm_output': '',
        'amount': 0.0,
        'type': 'Unknown',
        'transaction_source': '',
        'category': 'Unknown',
    }
    
    return {**defaults, **{k: v for k, v in json_obj.items() if v is not None}}

def setup_database() -> sqlite3.Connection:
    """Set up SQLite database with improved schema."""
    conn = sqlite3.connect('sms.db')
    cursor = conn.cursor()
    
    create_table_query = '''
    CREATE TABLE IF NOT EXISTS sms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        source TEXT,
        destination TEXT,
        body TEXT,
        body_md5 TEXT UNIQUE,
        llm_output TEXT,
        amount REAL,
        type TEXT,
        transaction_source TEXT,
        category TEXT
    )
    '''
    cursor.execute(create_table_query)
    return conn

def save_to_sqlite(output: List[Dict]):
    """Save analyzed data to SQLite with improved error handling."""
    conn = setup_database()
    cursor = conn.cursor()
    
    insert_query = '''
    INSERT OR IGNORE INTO sms (
        date, source, destination, body, body_md5, llm_output,
        amount, type, transaction_source, category
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    '''
    
    try:
        for sms in output:
            sms = ensure_keys(sms)
            cursor.execute(insert_query, (
                sms['date'], sms['source'], sms['destination'],
                sms['body'], sms['body_md5'], sms['llm_output'],
                sms['amount'], sms['type'], sms['transaction_source'],
                sms['category']
            ))
        conn.commit()
    except Exception as e:
        logger.error(f"Database error: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def save_to_csv(output: List[Dict], filename: str = 'sms.csv'):
    """Save analyzed data to CSV with improved field handling."""
    fieldnames = [
        'date', 'source', 'destination', 'body', 'body_md5',
        'llm_output', 'amount', 'type', 'transaction_source',
        'category'
    ]
    
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            for sms in output:
                writer.writerow(ensure_keys(sms))
    except Exception as e:
        logger.error(f"CSV write error: {e}")
        raise

@app.command()
def main(
    xml_file: str = typer.Option(..., help="Path to the XML file containing SMS data"),
    n: Optional[int] = typer.Option(None, help="Number of SMS to analyze (optional)")
):
    """Process SMS data from XML file and store results."""
    try:
        sms_list = parse_sms_xml(xml_file)
        logger.info(f"Parsed {len(sms_list)} SMS messages from {xml_file}")
        
        # Process all messages if n is None, otherwise process n messages
        messages_to_process = sms_list[:n] if n is not None else sms_list
        output = analyze_sms_list(messages_to_process)
        
        save_to_sqlite(output)
        save_to_csv(output)
        
        logger.info(f"Successfully processed {len(output)} SMS messages")
        
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        raise

if __name__ == '__main__':
    app()