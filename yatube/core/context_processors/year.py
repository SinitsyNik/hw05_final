from datetime import datetime


def year(request):
    current_date = datetime.now()
    return {
        'year': current_date.year,
    }
