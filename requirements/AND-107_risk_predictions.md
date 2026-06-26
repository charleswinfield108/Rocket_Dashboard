# AND-107 Risk Predictions

## Overview

The chatbot surfaces the risk predictions and explanations from M4/M5 work. Not all elevators have risk predictions; the predictions table covers the ~500 elevators the model identified as highest risk.

## Required Query

**"Why is elevator [ID] flagged as high-risk?"**

The response must include the specific risk factors from the prediction data — not just a label like "high-risk." The chatbot should reference the actual values from the predictions table (risk score, confidence, predicted outcome, per-class probabilities, risk explanation) to explain why the model flagged the device.

## Handling Missing Predictions

When asked about an elevator that has no entry in the predictions table, the chatbot must clearly state that no prediction is available for that device rather than guessing or inferring a risk level.
