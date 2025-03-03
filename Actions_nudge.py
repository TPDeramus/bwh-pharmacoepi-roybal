# <Dependencies>
from azure.cognitiveservices.personalizer import PersonalizerClient
from azure.cognitiveservices.personalizer.models import RankableAction, RewardRequest, RankRequest
from msrest.authentication import CognitiveServicesCredentials

import datetime, json, os, time, uuid

# openencounter_yn Actions
def get_OpenEnc_actions():
    yesOpenEnc = RankableAction(id='yesOpenEnc', features=[{"OpenEnc": 1}])
    noOpenEnc = RankableAction(id='noOpenEnc', features=[{"OpenEnc": 0}])
    return [yesOpenEnc, noOpenEnc]

# simplification_yn Actions
def get_Simplification_actions():
    yesSimplification = RankableAction(id='yesSimplification', features=[{"Simplification": 1}])
    noSimplification = RankableAction(id='noSimplification', features=[{"Simplification": 0}])
    return [yesSimplification, noSimplification]

# coldstate_yn Actions
def get_ColdState_actions():
    yesColdState = RankableAction(id='yesColdState', features=[{"ColdState": 1}])
    noColdState = RankableAction(id='noColdState', features=[{"ColdState": 0}])
    return [yesColdState, noColdState]

# riskframing_yn Actions
def get_RiskFraming_actions():
    yesRiskFrame = RankableAction(id='yesRiskFrame', features=[{"RiskFraming": 1}])
    noRiskFrame = RankableAction(id='noRiskFrame', features=[{"RiskFraming": 0}])
    return [yesRiskFrame, noRiskFrame]
