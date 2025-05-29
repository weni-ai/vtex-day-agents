from weni import Tool
from weni.context import Context
from weni.responses import TextResponse
from datetime import datetime
import pytz
from dateutil import parser
from dateutil.relativedelta import relativedelta


class CalculateDateDifference(Tool):
    def execute(self, context: Context) -> TextResponse:
        # Get parameters
        start_date_str = context.parameters.get("start_date", "")
        end_date_str = context.parameters.get("end_date", "")
        
        # Define BRT timezone (GMT-03:00)
        brt_tz = pytz.timezone('America/Sao_Paulo')
        
        try:
            # Parse dates flexibly
            start_date = self.parse_date(start_date_str, brt_tz)
            end_date = self.parse_date(end_date_str, brt_tz)
            
            # Calculate the difference
            result = self.calculate_difference(start_date, end_date)
            
            # Format response
            response_data = {
                "status": "success",
                "timezone": "BRT (GMT-03:00)",
                "start_date": start_date.strftime("%Y-%m-%d %H:%M:%S %Z"),
                "end_date": end_date.strftime("%Y-%m-%d %H:%M:%S %Z"),
                "difference": result
            }
            
            return TextResponse(data=response_data)
            
        except Exception as e:
            return TextResponse(data={
                "status": "error",
                "message": f"Error calculating date difference: {str(e)}",
                "hint": "Please provide dates in formats like DD/MM/YYYY, YYYY-MM-DD, or ISO format"
            })
    
    def parse_date(self, date_str, timezone):
        """Parse date string and convert to BRT timezone"""
        try:
            # Try to parse the date
            parsed_date = parser.parse(date_str, dayfirst=True)
            
            # If the date is naive (no timezone), localize it to BRT
            if parsed_date.tzinfo is None:
                parsed_date = timezone.localize(parsed_date)
            else:
                # Convert to BRT if it has a different timezone
                parsed_date = parsed_date.astimezone(timezone)
            
            return parsed_date
        except Exception as e:
            raise ValueError(f"Could not parse date '{date_str}': {str(e)}")
    
    def calculate_difference(self, start_date, end_date):
        """Calculate comprehensive difference between two dates"""
        # Determine which date is earlier
        if start_date > end_date:
            earlier, later = end_date, start_date
            is_negative = True
        else:
            earlier, later = start_date, end_date
            is_negative = False
        
        # Calculate total difference in various units
        total_seconds = int((later - earlier).total_seconds())
        total_minutes = total_seconds // 60
        total_hours = total_minutes // 60
        total_days = total_hours // 24
        
        # Calculate detailed breakdown using relativedelta
        rdelta = relativedelta(later, earlier)
        
        # Calculate remaining units
        remaining_hours = total_hours % 24
        remaining_minutes = total_minutes % 60
        remaining_seconds = total_seconds % 60
        
        # Build result
        result = {
            "is_negative": is_negative,
            "direction": "past" if is_negative else "future",
            "total": {
                "seconds": total_seconds,
                "minutes": total_minutes,
                "hours": total_hours,
                "days": total_days,
                "weeks": total_days // 7,
                "months_approx": total_days // 30,
                "years_approx": total_days // 365
            },
            "breakdown": {
                "years": rdelta.years,
                "months": rdelta.months,
                "days": rdelta.days,
                "hours": remaining_hours,
                "minutes": remaining_minutes,
                "seconds": remaining_seconds
            },
            "human_readable": self.format_human_readable(rdelta, remaining_hours, remaining_minutes, remaining_seconds, is_negative)
        }
        
        return result
    
    def format_human_readable(self, rdelta, hours, minutes, seconds, is_negative):
        """Format the difference in a human-readable way"""
        parts = []
        
        if rdelta.years > 0:
            parts.append(f"{rdelta.years} year{'s' if rdelta.years != 1 else ''}")
        if rdelta.months > 0:
            parts.append(f"{rdelta.months} month{'s' if rdelta.months != 1 else ''}")
        if rdelta.days > 0:
            parts.append(f"{rdelta.days} day{'s' if rdelta.days != 1 else ''}")
        if hours > 0:
            parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
        if minutes > 0:
            parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
        if seconds > 0 or len(parts) == 0:
            parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")
        
        # Join parts
        if len(parts) == 0:
            return "0 seconds"
        elif len(parts) == 1:
            result = parts[0]
        elif len(parts) == 2:
            result = f"{parts[0]} and {parts[1]}"
        else:
            result = ", ".join(parts[:-1]) + f", and {parts[-1]}"
        
        # Add direction indicator
        if is_negative:
            result = f"{result} ago"
        else:
            result = f"{result} ahead"
        
        return result 