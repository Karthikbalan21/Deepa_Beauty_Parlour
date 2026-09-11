from django.conf import settings
from django.db import models


def analyze_sentiment(text, rating=None):
    """
    Performs sentiment analysis using VADER sentiment analyzer with rating weighting.
    Returns a tuple of (sentiment_choice, compound_score).
    """
    compound = 0.0
    try:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
        analyzer = SentimentIntensityAnalyzer()
        scores = analyzer.polarity_scores(text or "")
        compound = scores.get("compound", 0.0)
    except Exception:
        lower = (text or "").lower()
        pos_words = {"great", "good", "excellent", "amazing", "love", "loved", "beautiful", "glow", "best", "perfect", "nice", "wonderful", "friendly", "satisfied"}
        neg_words = {"bad", "terrible", "worst", "horrible", "poor", "rude", "ruined", "ugly", "painful", "waste", "disappointed", "slow", "delay"}
        pos_count = sum(1 for w in pos_words if w in lower)
        neg_count = sum(1 for w in neg_words if w in lower)
        if pos_count > neg_count:
            compound = 0.5
        elif neg_count > pos_count:
            compound = -0.5
        else:
            compound = 0.0

    # Combine text polarity score with star rating context if available
    if rating is not None:
        if rating >= 4:
            sentiment = "POSITIVE" if compound >= -0.15 else "NEGATIVE"
        elif rating <= 2:
            sentiment = "NEGATIVE" if compound <= 0.2 else "POSITIVE"
        else:  # rating == 3
            if compound >= 0.1:
                sentiment = "POSITIVE"
            elif compound <= -0.1:
                sentiment = "NEGATIVE"
            else:
                sentiment = "NEUTRAL"
    else:
        if compound >= 0.05:
            sentiment = "POSITIVE"
        elif compound <= -0.05:
            sentiment = "NEGATIVE"
        else:
            sentiment = "NEUTRAL"

    return sentiment, round(float(compound), 3)


class Feedback(models.Model):
    class Sentiment(models.TextChoices):
        POSITIVE = "POSITIVE", "Positive"
        NEUTRAL = "NEUTRAL", "Neutral"
        NEGATIVE = "NEGATIVE", "Negative"

    RATING_CHOICES = [
        (5, "★★★★★ (5/5) Excellent"),
        (4, "★★★★☆ (4/5) Very Good"),
        (3, "★★★☆☆ (3/5) Good"),
        (2, "★★☆☆☆ (2/5) Fair"),
        (1, "★☆☆☆☆ (1/5) Poor"),
    ]

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="feedbacks"
    )
    appointment = models.ForeignKey(
        "appointments.Appointment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="feedbacks"
    )
    service = models.ForeignKey(
        "services.Service",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="feedbacks"
    )
    rating = models.PositiveSmallIntegerField(
        choices=RATING_CHOICES,
        default=5
    )
    comments = models.TextField(
        help_text="Customer review or feedback"
    )
    sentiment = models.CharField(
        max_length=15,
        choices=Sentiment.choices,
        default=Sentiment.NEUTRAL,
        db_index=True,
        help_text="Automated sentiment classification (Positive, Neutral, Negative)"
    )
    sentiment_score = models.FloatField(
        default=0.0,
        help_text="Polarity compound score (-1.0 to +1.0)"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.customer.username} - {self.rating} stars ({self.sentiment})"

    def save(self, *args, **kwargs):
        sentiment, score = analyze_sentiment(self.comments, self.rating)
        self.sentiment = sentiment
        self.sentiment_score = score
        super().save(*args, **kwargs)
