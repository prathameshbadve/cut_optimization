from django.db import models

# Create your models here.
class StockLength(models.Model):

    length = models.IntegerField()

    def __str__(self) -> str:
        return f"{self.length}"
    
class DemandLength(models.Model):

    length = models.IntegerField(help_text="Cutting Length in mm")
    qty = models.IntegerField()
    code = models.CharField(max_length=20)

    def __str__(self):
        return f"{self.code} - {self.length}mm x {self.qty}"