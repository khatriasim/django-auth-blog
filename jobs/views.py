from django.shortcuts import render
from .scraper import scrape_linkedin_jobs, save_jobs
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .tasks  import scrape_jobs_task


# class ScrapeJobView(APIView):

#     def get(self, request):
#         keyword = "react"
#         location = "nepal"
#         jobs = scrape_linkedin_jobs(keyword, location)
#         result = save_jobs(jobs)

#         return Response(
#             {
#                 'message': 'Data scraped successfully',
#                 'scraped': len(jobs),
#                 **result,
#             },
#             status=status.HTTP_200_OK
#         )

class ScrapeJobView(APIView):
    def get(self, request):
        task = scrape_jobs_task.delay("ml ai", "india")
        return Response({
            'message': 'Scraping started',
            'task_id': task.id  
        }, status=status.HTTP_200_OK)