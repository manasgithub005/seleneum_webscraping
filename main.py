import os
import pandas as pd
import json
from loguru import logger
from bestbuy_review_scraper import BestBuyReviewScraper
from review_analyzer import ReviewAnalyzer

def main():
    """Main function to run the Best Buy review scraping and analysis"""
    # Configure logger
    logger.add("bestbuy_scraper.log", rotation="10 MB")
    logger.info("Starting Best Buy review scraping and analysis")
    
    # Get product URL from user
    product_url = input("Enter Best Buy Canada product URL: ")
    max_reviews = input("Maximum number of reviews to scrape (leave blank for all): ")
    max_reviews = int(max_reviews) if max_reviews.strip() else None
    
    # Select filter option
    print("\nSelect filter option:")
    filters = {
        "1": "most-helpful", 
        "2": "newest", 
        "3": "highest-rating", 
        "4": "lowest-rating", 
        "5": "most-relevant"
    }
    for key, value in filters.items():
        print(f"{key}: {value}")
    
    filter_choice = input("Enter choice (1-5): ")
    filter_option = filters.get(filter_choice, "most-helpful")
    
    # Create output directory if it doesn't exist
    output_dir = "bestbuy_results"
    os.makedirs(output_dir, exist_ok=True)
    
    # Configure file paths
    product_id = product_url.split('/')[-1]
    raw_csv_path = os.path.join(output_dir, f"bestbuy_{product_id}_reviews_raw.csv")
    analyzed_csv_path = os.path.join(output_dir, f"bestbuy_{product_id}_reviews_analyzed.csv")
    analyzed_excel_path = os.path.join(output_dir, f"bestbuy_{product_id}_reviews_analyzed.xlsx")
    insights_path = os.path.join(output_dir, f"bestbuy_{product_id}_insights.json")
    report_path = os.path.join(output_dir, f"bestbuy_{product_id}_report.txt")
    
    # Step 1: Scrape reviews
    logger.info("Initializing scraper")
    scraper = BestBuyReviewScraper(headless=False)
    
    try:
        logger.info(f"Scraping reviews for product: {product_url}")
        reviews_df = scraper.scrape_product_reviews(
            product_url=product_url,
            filter_option=filter_option,
            max_reviews=max_reviews
        )
        
        if reviews_df is None or reviews_df.empty:
            logger.error("No reviews were scraped. Check the URL and try again.")
            return
        
        # Save raw data
        reviews_df.to_csv(raw_csv_path, index=False)
        logger.info(f"Raw reviews saved to {raw_csv_path}")
        
        # Step 2: Analyze reviews
        logger.info("Initializing analyzer")
        analyzer = ReviewAnalyzer()
        
        logger.info("Analyzing reviews")
        analyzed_df = analyzer.analyze_reviews(reviews_df)
        
        # Save analyzed data
        analyzed_df.to_csv(analyzed_csv_path, index=False)
        analyzed_df.to_excel(analyzed_excel_path, index=False)
        logger.info(f"Analyzed reviews saved to {analyzed_csv_path} and {analyzed_excel_path}")
        
        # Step 3: Extract insights and generate recommendations
        logger.info("Extracting insights")
        insights = analyzer.extract_insights(analyzed_df)
        
        logger.info("Generating recommendations")
        recommendations = analyzer.generate_recommendations(insights)
        
        # Save insights
        with open(insights_path, 'w') as f:
            json.dump(insights, f, indent=4)
        logger.info(f"Insights saved to {insights_path}")
        
        # Generate and save report
        generate_report(report_path, product_url, insights, recommendations, len(reviews_df))
        logger.info(f"Report saved to {report_path}")
        
        logger.success("Process completed successfully!")
        print(f"\nResults saved to {output_dir} directory")
        print(f"Report: {report_path}")
        
    except Exception as e:
        logger.error(f"Error in main process: {e}")
    finally:
        # Clean up
        if 'scraper' in locals():
            del scraper

def generate_report(report_path, product_url, insights, recommendations, total_reviews):
    """Generate a text report with insights and recommendations"""
    with open(report_path, 'w') as f:
        f.write("BEST BUY CANADA REVIEW ANALYSIS REPORT\n")
        f.write("=" * 50 + "\n\n")
        
        f.write(f"Product URL: {product_url}\n")
        f.write(f"Total Reviews Analyzed: {total_reviews}\n\n")
        
        f.write("REVIEW STATISTICS\n")
        f.write("-" * 20 + "\n")
        f.write(f"Average Rating: {insights.get('average_rating', 'N/A'):.2f}/5.0\n\n")
        
        f.write("Rating Distribution:\n")
        rating_dist = insights.get('rating_distribution', {})
        for rating in sorted(rating_dist.keys(), reverse=True):
            count = rating_dist[rating]
            percentage = (count / total_reviews) * 100 if total_reviews > 0 else 0
            f.write(f"{rating} stars: {count} reviews ({percentage:.1f}%)\n")
        
        f.write("\nSentiment Distribution:\n")
        sentiment_dist = insights.get('sentiment_distribution', {})
        for sentiment, count in sentiment_dist.items():
            percentage = (count / total_reviews) * 100 if total_reviews > 0 else 0
            f.write(f"{sentiment}: {count} reviews ({percentage:.1f}%)\n")
        
        f.write("\nCategory Distribution:\n")
        category_dist = insights.get('category_distribution', {})
        for category, count in category_dist.items():
            percentage = (count / total_reviews) * 100 if total_reviews > 0 else 0
            f.write(f"{category}: {count} reviews ({percentage:.1f}%)\n")
        
        f.write("\nCOMMON THEMES\n")
        f.write("-" * 20 + "\n")
        
        f.write("Positive Themes:\n")
        positive_words = insights.get('top_positive_words', {})
        for word, count in list(positive_words.items())[:10]:
            f.write(f"- {word}: {count} occurrences\n")
        
        f.write("\nNegative Themes:\n")
        negative_words = insights.get('top_negative_words', {})
        for word, count in list(negative_words.items())[:10]:
            f.write(f"- {word}: {count} occurrences\n")
        
        f.write("\nBUSINESS RECOMMENDATIONS\n")
        f.write("-" * 20 + "\n")
        for i, rec in enumerate(recommendations, 1):
            f.write(f"{i}. {rec}\n")
        
        f.write("\nSCRAPING CHALLENGES\n")
        f.write("-" * 20 + "\n")
        f.write("1. The scraper had to handle dynamic content loading and 'Show More' buttons.\n")
        f.write("2. User agent rotation was implemented to avoid detection.\n")
        f.write("3. Random wait times between actions were used to simulate human browsing.\n")
        f.write("4. The structure of the Best Buy website might change, requiring updates to selectors.\n")
        
        f.write("\n" + "=" * 50 + "\n")
        f.write("Report generated by Best Buy Review Analyzer")

if __name__ == "__main__":
    main()
