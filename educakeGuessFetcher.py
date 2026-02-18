from curl_cffi import requests
import tkinter as tk

# --------
# BACK-END 
# --------

# Declaring session variables 

# Define payload
loginPayload={"username" : "", "password" : "", "lastname" : "", "userType" : "student","allowEmailForUsername" : True}

# Define request headers for GET and POST HTTPS requests
headers = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:146.0) Gecko/20100101 Firefox/146.0",
    "Content-Type": "application/json",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-GB,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Origin": "https://my.educake.co.uk",
    "Referer": "https://my.educake.co.uk/student-login",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "Sec-CH-UA": '"Chromium";v="120", "Google Chrome";v="120"',
    "Sec-CH-UA-Mobile": "?0",
    "Sec-CH-UA-Platform": '"Linux"',
    "Connection": "keep-alive",
}

# Define dictionary that will contain correctAnswers of quiz
correctAnswersDict={}

# Create session impersonating a chrome browser request
loginSession=requests.Session(impersonate="chrome120")

# Functions

def getTokens(loginPayload,verbose=False):# Function to get session XSRF-TOKEN, get/generate JWT-TOKEN and accumulate session cookies
    global loginHeaders,loginSession
    
    #URLs
    frontEndLoginURL="https://my.educake.co.uk/student-login"
    loginURL="https://my.educake.co.uk/login"
    sessionTokenURL="https://my.educake.co.uk/session-token"

    # Step 1- Send GET to front-end login page (just used to get XSRF-TOKEN instance, could be any page, but this one has no redirects)
    frontEndLoginPageResponse=loginSession.get(frontEndLoginURL,headers=headers)#send GET request
    if verbose:print(f"Front-end page request finished with code {frontEndLoginPageResponse.status_code}, starting api-based login page request...\n\n\n")

    oXSRFTOKEN=(loginSession.cookies.get_dict())['XSRF-TOKEN']#get site cookies stored in current session, extract XSRF-TOKEN
    headers["X-XSRF-TOKEN"]=oXSRFTOKEN#Add to login headers

    # Step 2- Send POST to the real login API, by sending Educake the login details in loginPayload, and Educake will refresh XSRF-TOKEN
    # giving access/authorization to get a JWT token from my.educake.co.uk/session-token
    apiLoginPageResponse = loginSession.post(loginURL,headers=headers,json=loginPayload)# send POST request with payload/login info
    if verbose:print(f"Finished API login page response with code {apiLoginPageResponse.status_code}\n\n\n")

    XSRF_TOKEN=(apiLoginPageResponse.cookies.get_dict())['XSRF-TOKEN']# Get new XSRF-TOKEN
    headers['X-XSRF-TOKEN']= XSRF_TOKEN# Replace old XSRF-TOKEN with new, permanent one

    # Step 3- Take new XSRF-TOKEN and permissions, send GET to Educake session-token generator to create session-token (aka. JWT-TOKEN)
    sessionTokenPageResponse = loginSession.get(sessionTokenURL,headers=headers)# send GET request
    if verbose:print(f"Session token URL finished with code {sessionTokenPageResponse.status_code}")

    sessionToken=sessionTokenPageResponse.json();sessionToken=sessionToken['accessToken']# Get the sent .json file, extract JWT-TOKEN
    JWT_TOKEN=f"Bearer {sessionToken}"# Add 'Bearer' tag

    if verbose:print("TOKEN fetching is done! Moving onto answer fetching...\n\n\n")

    return [XSRF_TOKEN,JWT_TOKEN]



def getUserCredentialsAndAddToHeader(verbose=False):# Function to get user credentials, checks validity, adds to request header and saves to file
    global loginPayload
    uName,uPass="",""
    try: # If credentials file is found, and credentials are valid, assign the credentials to the login payload
        userCredFile=open("educakeCredentials.txt","r")
        credentials=userCredFile.read().split("\n")
        uName=credentials[0]
        uPass=credentials[1]
        loginPayload['username']=uName
        loginPayload['password']=uPass
        getTokens(loginPayload)

    except:
        print("No credentials file was found, or was invalid. Creating one now...\n\n")
        validCredentials=False
        while not(validCredentials):
            getUsername=str(input("Enter your educake username\t"))
            getPassword=str(input("\n\nEnter your Educake password\t"))
            try: 
                loginPayload["username"]=getUsername
                loginPayload["password"]=getPassword
                getTokens(loginPayload,verbose=verbose)
                print("\n\nCredentials authorized, saving them now...")
                uName=getUsername
                uPass=getPassword
                validCredentials=True
            except KeyError:
                print("\n\nCredentials invalid, maybe there was a typo?")

        userCredFile=open("educakeCredentials.txt","w")
        userCredFile.write(f"{uName}\n{uPass}")



def getQuizURL(browserURL):# Pretty self explanitory
    splitURL=browserURL.split("/");quizID=splitURL[-1]
    return f"https://my.educake.co.uk/api/student/quiz/{quizID}"



def fetchQuizAnswers(quizBrowserURL,verbose=False):
    global correctAnswersDict

    # Get username and password, add to request headers
    getUserCredentialsAndAddToHeader()

    # Defining security tokens for request headers
    tokens=getTokens(loginPayload)

    XSRF_TOKEN=tokens[0]

    JWT_TOKEN=tokens[1]

    # Updating headers with JWT-TOKEN and XSRF-TOKEN
    headers['Authorization']= JWT_TOKEN
    headers['X-XSRF-TOKEN']= XSRF_TOKEN

    # Get quiz URL
    urlToGoTo=getQuizURL(quizBrowserURL)

    # Send GET request to questionIDs URL
    urlResponse=loginSession.get(urlToGoTo,headers=headers)


    if verbose:print(f"Got question IDs with code{urlResponse.status_code}, reason {urlResponse.reason}")

    # Records text of URL
    responseAsText=urlResponse.text


    # Sets start and end of where to look (starts at 'questions', finishes at end of questionIDs list)
    start = responseAsText.find("\"questions\":[")
    end = responseAsText.find(",\"questionMap\"")

    # Puts into iterable list format
    questionIDs=((responseAsText[start:end]).replace("\"questions\":[","")).split(",")# Gets questionIDs in list form
    
    # Defining base answer URL template
    baseAnswerURL="https://my.educake.co.uk/api/course/question/"
    
    # Defining answers dictionary
    
    # Iterating through questionsIDs and getting answers
    for i in range(len(questionIDs)):
        
        # Filling in URL with QuestionID
        answerURL=f"{baseAnswerURL}{questionIDs[i]}/mark"
        
        # Defining dummy answer to send via POST
        sendPrompt={"givenAnswer" : "-1"}

        # Send POST request to URL, with dummy answer and headers, then get text reponse from page
        answerURLresponse=loginSession.post(answerURL,headers=headers,json=sendPrompt)
        answerResponseAsText=answerURLresponse.text


        # Define start point of 'correctAnswers'
        nstart=answerResponseAsText.find("\"correctAnswers\":[")

        # Define end point of 'correctAnswers'
        nend=answerResponseAsText.find("],\"reasoning\":")

        # Extract answer
        correctAnswer=((answerResponseAsText[nstart:nend]).replace("\"correctAnswers\":[","")).replace("\"","").split(",")[0]

        # Print answer, add to LUT and ARR
        print(f"Question {i+1} answer: {correctAnswer}")
        correctAnswersDict[f"Q{i+1}"]= correctAnswer

fetchQuizAnswers(url:=str(input("Enter the quiz URL\t")))

