class StoryPointsCalculator:
    def calculate(self, complexity: str, files_impacted: int, risk_level: str) -> int:
        if complexity == "HIGH" or risk_level == "HIGH" or files_impacted > 10:
            points = min(8 + files_impacted // 2, 13)
        elif complexity == "MEDIUM" or files_impacted >= 3:
            points = 5
        else:
            points = 2
        return max(1, min(points, 13))
