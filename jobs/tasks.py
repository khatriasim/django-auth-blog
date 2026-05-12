from celery import shared_task
from .scraper import scrape_linkedin_jobs, save_jobs

@shared_task
def scrape_jobs_task(keyword, location):
    jobs = scrape_linkedin_jobs(keyword, location)
    result = save_jobs(jobs)
    return (
        f"Scraped {len(jobs)} jobs, "
        f"saved {result['saved']}, "
        f"updated {result['updated']}, "
        f"skipped {result['skipped']}"
    )
