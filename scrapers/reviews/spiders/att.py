# -*- coding: utf-8 -*-
import scrapy
import json
import arrow

from urllib.parse import urlencode

class AttSpider(scrapy.Spider):
    name = 'att'
    allowed_domains = ['www.att.com', 'api.bazaarvoice.com']
    start_urls = ['https://www.att.com/cellphones/iphone/apple-iphone-x.html']

    # Custom params
    api_query_params = {
        'passkey': '9v8vw9jrx3krjtkp26homrdl8',
        'apiversion': '5.5',
        'displaycode': '4773-en_us',
        'resource.q0': 'reviews',
        'filter.q0': 'isratingsonly:eq:false',
        'filter.q0': 'contentlocale:eq:en_US',
        'sort.q0': 'relevancy:a1',
        'stats.q0': 'reviews',
        'filteredstats.q0': 'reviews',
        'include.q0': 'authors,products,comments',
        'filter_reviews.q0': 'contentlocale:eq:en_US',
        'filter_reviewcomments.q0': 'contentlocale:eq:en_US',
        'filter_comments.q0': 'contentlocale:eq:en_US',
        'limit_comments.q0': '3',
    }
    api_endpoint_url = "https://api.bazaarvoice.com/data/batch.json"

    def _generate_review_api_url(self, sku, limit=100, offset=0):
        query_params = {**self.api_query_params, **{
            'limit.q0': int(limit),
            'offset.q0': int(offset),
            'filter.q0': 'productid:eq:sku{}'.format(sku)
        }}
        return "{}?{}".format(self.api_endpoint_url, urlencode(query_params))


    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(url=url, callback=self.parse_product_page)


    def parse_product_page(self, response):
        sku = response.css('#content [itemprop="sku"]::attr(content)').extract_first()
        if sku:
            sku = sku.strip()[3:]
            yield scrapy.Request(
                url=self._generate_review_api_url(sku, limit=100, offset=0),
                callback=self.parse_reviews,
                meta={'request': {'limit': 100, 'offset': 0}, 'product': {'sku': sku}})


    def parse_reviews(self, response):
        limit = response.meta['request']['limit']
        offset = response.meta['request']['offset']
        sku = response.meta['product']['sku']
        body = response.text

        try:
            data = json.loads(body)
            total = data['BatchedResults']['q0']['TotalResults']
            reviews = data['BatchedResults']['q0']['Results']
        except KeyError as e:
            raise e
            return
        except Exception as e:
            raise e
            return

        for review in reviews:
            title = review['Title']
            text = review['ReviewText']
            comments = review['TotalCommentCount']
            ups = review['TotalPositiveFeedbackCount']
            downs = review['TotalNegativeFeedbackCount']
            rating = review['Rating']
            user = review['UserNickname']
            try:
                date = arrow.get(review['SubmissionTime'])
            except Exception as e:
                date = None

            if title:
                title = title.strip()
            if text:
                text = text.strip()
            if user:
                user = user.strip()
            if date:
                date = date.isoformat()

            yield {
                'product_sku': sku,
                'review_username': user,
                'review_title': title,
                'review_text': text,
                'review_date': date,
                'review_ups': ups,
                'review_downs': downs,
                'review_rating': rating
            }

        if len(reviews) == limit:
            offset = offset + limit
            yield scrapy.Request(
                url=self._generate_review_api_url(sku, limit=100, offset=offset),
                callback=self.parse_reviews,
                meta={'request': {'limit': 100, 'offset': offset}, 'product': {'sku': sku}},
                dont_filter=True)
