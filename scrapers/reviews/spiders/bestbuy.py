# -*- coding: utf-8 -*-
import scrapy
import arrow

class BestBuySpider(scrapy.Spider):
    name = 'bestbuy'
    allowed_domains = ['bestbuy.com']
    start_urls = ['https://www.bestbuy.com/site/iphone/iphone-x/pcmcat1505326434742.c?id=pcmcat1505326434742']

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(url=url, callback=self.parse_products)


    def parse_products(self, response):
        # Fetch products on page
        products = response.css('.list-item')
        for product in products:
            title = product.css('h4 a::text').extract_first().strip()
            url = product.css('.product-options a::attr(href)').extract_first()
            model = product.css('.model-number .sku-value::text').extract_first().strip()
            sku = product.css('.sku-id .sku-value::text').extract_first().strip()
            if url:
                # Follow the product page
                product = {
                    'title': title,
                    'url': url,
                    'model': model,
                    'sku': sku
                }
                yield response.follow(url=url, callback=self.parse_product_page, meta={'product': product})


    def parse_product_page(self, response):
        # Fetch the link to all reviews
        all_reviews_link = response.css('.ugc-reviews h2 a::attr(href)').extract_first()
        if all_reviews_link and "reviews" in all_reviews_link:
            yield response.follow(url=all_reviews_link, callback=self.parse_reviews, meta=response.meta)


    def parse_reviews(self, response):
        # Figure out on which page we're in
        product = response.meta["product"]
        try:
            page = int(response.meta["page"])
        except Exception as e:
            page = 1

        # Fetch review blocks
        reviews = response.css('.review-item')
        if not reviews:
            return
        for review in reviews:
            title = review.css('h4::text').extract_first().strip()
            text = review.css('.review-content p::text').extract_first().strip()
            date = review.css('.review-date::text').extract_first()
            ups = review.css('.feedback-display a[data-track="Helpful"]::attr(data-pos-count)').extract_first()
            downs = review.css('.feedback-display a[data-track="Unhelpful"]::attr(data-neg-count)').extract_first()
            rating = review.css('.reviewer-score::text').extract_first()

            if date:
                try:
                    date = arrow.get(date, 'MMMM D, YYYY')
                except Exception as e:
                    # Log something ? YOLO
                    pass

            if ups:
                ups = int(ups)
            if downs:
                downs = int(downs)
            if rating:
                rating = int(rating)

            yield {
                'product_title': product['title'],
                'product_model': product['model'],
                'product_sku': product['sku'],
                'review_rating': rating,
                'review_page': page,
                'review_title': title,
                'review_text': text,
                'review_date': date.isoformat(),
                'review_ups': ups,
                'review_downs': downs
            }

        # Check if there is another page of reviews to follow
        next_page = response.css('.pagination.ugc li.active + li a::attr(href)').extract_first()
        if next_page:
            yield scrapy.Request(url=next_page, callback=self.parse_reviews, meta={'product': product, 'page': page+1})
