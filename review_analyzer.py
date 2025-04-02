import re
import pandas as pd
import numpy as np
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from tqdm import tqdm
from loguru import logger

class ReviewAnalyzer:
    def __init__(self):
        """Initialize the Review Analyzer with required NLTK resources"""
        logger.info("Initializing Review Analyzer")
        
        # Download required NLTK resources
        try:
            nltk.download('punkt', quiet=True)
            nltk.download('stopwords', quiet=True)
            nltk.download('vader_lexicon', quiet=True)
            self.stop_words = set(stopwords.words('english'))
            self.sentiment_analyzer = SentimentIntensityAnalyzer()
        except Exception as e:
            logger.error(f"Error downloading NLTK resources: {e}")
            raise
    
    def preprocess_text(self, text):
        """
        Preprocess the text by cleaning, tokenizing and removing stopwords
        
        Args:
            text (str): The text to preprocess
            
        Returns:
            str: Preprocessed text
        """
        if not isinstance(text, str):
            return ""
        
        # Convert to lowercase
        text = text.lower()
        
        # Remove special characters and numbers
        text = re.sub(r'[^\w\s]', '', text)
        text = re.sub(r'\d+', '', text)
        
        # Tokenize
        tokens = word_tokenize(text)
        
        # Remove stopwords
        tokens = [word for word in tokens if word not in self.stop_words]
        
        # Join back into text
        return ' '.join(tokens)
    
    def analyze_sentiment(self, text):
        """
        Analyze the sentiment of the text using VADER
        
        Args:
            text (str): The text to analyze
            
        Returns:
            dict: Sentiment scores
        """
        if not isinstance(text, str) or not text.strip():
            return {
                'compound': 0,
                'neg': 0,
                'neu': 0,
                'pos': 0
            }
        
        return self.sentiment_analyzer.polarity_scores(text)
    
    def categorize_sentiment(self, compound_score, rating=None):
        """
        Categorize sentiment based on compound score and rating
        
        Args:
            compound_score (float): Compound sentiment score
            rating (int, optional): Rating out of 5
            
        Returns:
            tuple: (sentiment category, specific category)
        """
        # Base categorization on sentiment score
        if compound_score >= 0.05:
            sentiment = "Positive"
            if compound_score >= 0.75:
                specific = "Highly Satisfactory & Recommended"
            else:
                specific = "Good Design & Quality"
        elif compound_score <= -0.05:
            sentiment = "Negative"
            if compound_score <= -0.75:
                specific = "Very Poor Quality & Not Recommended"
            else:
                specific = "Poor Quality"
        else:
            sentiment = "Neutral"
            specific = "Mixed Feelings"
        
        # Adjust based on rating if available
        if rating is not None:
            if rating >= 4 and sentiment != "Positive":
                sentiment = "Positive"
                specific = "Good Design & Quality"
            elif rating <= 2 and sentiment != "Negative":
                sentiment = "Negative"
                specific = "Poor Quality"
        
        return sentiment, specific
    
    def analyze_reviews(self, reviews_df):
        """
        Process and analyze reviews
        
        Args:
            reviews_df (pandas.DataFrame): DataFrame with reviews
            
        Returns:
            pandas.DataFrame: Processed DataFrame with sentiment analysis
        """
        logger.info("Analyzing reviews")
        
        if reviews_df.empty:
            logger.warning("No reviews to analyze")
            return reviews_df
        
        # Create a copy to avoid modifying the original
        df = reviews_df.copy()
        
        # Preprocess review text
        logger.info("Preprocessing review text")
        df['processed_text'] = df['review_text'].apply(lambda x: self.preprocess_text(x))
        
        # Analyze sentiment
        logger.info("Analyzing sentiment")
        sentiment_results = []
        
        for idx, row in tqdm(df.iterrows(), total=len(df), desc="Analyzing sentiment"):
            # Get sentiment scores for both title and review
            title_scores = self.analyze_sentiment(row['title'])
            review_scores = self.analyze_sentiment(row['review_text'])
            
            # Combine scores (give more weight to review text)
            compound_score = 0.3 * title_scores['compound'] + 0.7 * review_scores['compound']
            
            # Categorize sentiment
            sentiment, specific_category = self.categorize_sentiment(compound_score, row.get('rating'))
            
            sentiment_results.append({
                'compound_score': compound_score,
                'sentiment': sentiment,
                'specific_category': specific_category
            })
        
        # Add sentiment results to DataFrame
        sentiment_df = pd.DataFrame(sentiment_results)
        df = pd.concat([df, sentiment_df], axis=1)
        
        logger.success(f"Sentiment analysis completed for {len(df)} reviews")
        return df
    
    def extract_insights(self, df):
        """
        Extract insights from analyzed reviews
        
        Args:
            df (pandas.DataFrame): DataFrame with analyzed reviews
            
        Returns:
            dict: Dictionary with insights
        """
        logger.info("Extracting insights from reviews")
        
        if df.empty:
            logger.warning("No reviews to extract insights from")
            return {}
        
        insights = {
            'total_reviews': len(df),
            'average_rating': df['rating'].mean(),
            'sentiment_distribution': df['sentiment'].value_counts().to_dict(),
            'category_distribution': df['specific_category'].value_counts().to_dict(),
            'rating_distribution': df['rating'].value_counts().sort_index().to_dict()
        }
        
        # Find most common words in positive reviews
        positive_reviews = df[df['sentiment'] == 'Positive']
        if not positive_reviews.empty:
            positive_text = ' '.join(positive_reviews['processed_text'].tolist())
            positive_tokens = word_tokenize(positive_text)
            positive_word_freq = nltk.FreqDist(positive_tokens)
            insights['top_positive_words'] = dict(positive_word_freq.most_common(10))
        
        # Find most common words in negative reviews
        negative_reviews = df[df['sentiment'] == 'Negative']
        if not negative_reviews.empty:
            negative_text = ' '.join(negative_reviews['processed_text'].tolist())
            negative_tokens = word_tokenize(negative_text)
            negative_word_freq = nltk.FreqDist(negative_tokens)
            insights['top_negative_words'] = dict(negative_word_freq.most_common(10))
        
        logger.success("Insights extraction completed")
        return insights
    
    def generate_recommendations(self, insights):
        """
        Generate business recommendations based on insights
        
        Args:
            insights (dict): Dictionary with insights
            
        Returns:
            list: List of recommendations
        """
        logger.info("Generating business recommendations")
        
        recommendations = []
        
        # Check if we have enough data
        if insights.get('total_reviews', 0) < 5:
            recommendations.append("Collect more customer reviews to make meaningful recommendations.")
            return recommendations
        
        # Check overall sentiment
        sentiment_dist = insights.get('sentiment_distribution', {})
        positive_pct = sentiment_dist.get('Positive', 0) / insights['total_reviews'] * 100 if insights['total_reviews'] > 0 else 0
        negative_pct = sentiment_dist.get('Negative', 0) / insights['total_reviews'] * 100 if insights['total_reviews'] > 0 else 0
        
        if positive_pct >= 70:
            recommendations.append("Customer satisfaction is high. Maintain current quality standards and focus on expanding product features.")
        elif negative_pct >= 30:
            recommendations.append("Significant customer dissatisfaction detected. Address common complaints urgently.")
        
        # Analyze negative reviews for improvement areas
        if 'top_negative_words' in insights:
            negative_themes = list(insights['top_negative_words'].keys())
            if negative_themes:
                recs = "Focus on improving these aspects: " + ", ".join(negative_themes[:5])
                recommendations.append(recs)
        
        # Analyze positive reviews for strengths
        if 'top_positive_words' in insights:
            positive_themes = list(insights['top_positive_words'].keys())
            if positive_themes:
                recs = "Highlight these strengths in marketing materials: " + ", ".join(positive_themes[:5])
                recommendations.append(recs)
        
        # Rating-based recommendations
        avg_rating = insights.get('average_rating', 0)
        if avg_rating < 3.0:
            recommendations.append("Overall rating is below average. Consider a product redesign or feature improvements.")
        elif avg_rating >= 4.5:
            recommendations.append("Excellent product rating. Consider using customer testimonials in marketing campaigns.")
        
        logger.success(f"Generated {len(recommendations)} business recommendations")
        return recommendations

# Example usage
if __name__ == "__main__":
    # Load reviews from CSV
    reviews_df = pd.read_csv("bestbuy_reviews.csv")
    
    analyzer = ReviewAnalyzer()
    analyzed_df = analyzer.analyze_reviews(reviews_df)
    
    # Save processed data
    analyzed_df.to_csv("bestbuy_reviews_analyzed.csv", index=False)
    analyzed_df.to_excel("bestbuy_reviews_analyzed.xlsx", index=False)
    
    # Generate insights and recommendations
    insights = analyzer.extract_insights(analyzed_df)
    recommendations = analyzer.generate_recommendations(insights)
    
    print("Insights:", insights)
    print("\nRecommendations:")
    for rec in recommendations:
        print(f"- {rec}")
