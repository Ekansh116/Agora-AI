import re
from datetime import datetime
from typing import List, Dict
from dateutil import parser as date_parser

class ParserService:
    def __init__(self):
        # Matches Android/Web format: "dd/mm/yyyy, hh:mm - Body" (with optional commas and dot-separated AM/PM)
        self.android_re = re.compile(
            r'^(\d{1,4}[/\-.]\d{1,2}[/\-.]\d{1,4}),?\s*(\d{1,2}:\d{2}(?::\d{2})?(?:\s*[AaPp]\.?\s*[Mm]\.?)?)\s*-\s*(.*)$'
        )
        # Matches iOS format: "[dd/mm/yyyy, hh:mm:ss] Body" (with optional commas and dot-separated AM/PM)
        self.ios_re = re.compile(
            r'^\[(\d{1,4}[/\-.]\d{1,2}[/\-.]\d{1,4}),?\s*(\d{1,2}:\d{2}(?::\d{2})?(?:\s*[AaPp]\.?\s*[Mm]\.?)?)\]\s*(.*)$'
        )

    def parse(self, text: str) -> List[Dict]:
        """
        Parse raw WhatsApp chat export contents into a list of messages.
        Each message is a dictionary containing:
        - timestamp: datetime object
        - sender: str (username)
        - content: str (message text)
        """
        lines = text.splitlines()
        parsed_messages = []
        current_msg = None

        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue

            match = None
            
            # Check for iOS format first
            ios_match = self.ios_re.match(line_str)
            if ios_match:
                match = ios_match
            else:
                # Check for Android/Web format
                android_match = self.android_re.match(line_str)
                if android_match:
                    match = android_match

            if match:
                # Save previous message if it exists
                if current_msg and current_msg.get("sender") and current_msg.get("content"):
                    parsed_messages.append(current_msg)
                    current_msg = None

                date_str, time_str, body = match.groups()
                datetime_str = f"{date_str} {time_str}"
                
                try:
                    # parse with dayfirst=True since WhatsApp exports frequently use dd/mm/yyyy
                    timestamp = date_parser.parse(datetime_str, dayfirst=True)
                except Exception:
                    timestamp = datetime.utcnow()

                # Message body must contain a colon separation (Sender: Message)
                if ": " in body:
                    sender, content = body.split(": ", 1)
                    current_msg = {
                        "timestamp": timestamp,
                        "sender": sender.strip(),
                        "content": content.strip()
                    }
                else:
                    # System notifications (e.g. joined/left notifications, group encryption notice)
                    current_msg = None
            else:
                # Append to current message if it's a multi-line block
                if current_msg:
                    current_msg["content"] += "\n" + line_str

        # Append last remaining message
        if current_msg and current_msg.get("sender") and current_msg.get("content"):
            parsed_messages.append(current_msg)

        return parsed_messages
