import os.path
import sys

from selenium import webdriver
from selenium.common import ElementClickInterceptedException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re
import time
from configparser import RawConfigParser





class AutoRQM(object):
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(sys.argv[0])))) #PY文件所在的文件目录
        self.config = RawConfigParser() #读取ini文件的对象
        self.driver = None
        self.timeout = 60
        self.poll_frequency = 0.5
        self.current_time_line = ""
        self.feature_template = ""
        self.tasks_section = ['TCReq', 'TCDev', 'TCAuto', 'TCExe']
        self.ini_section_validation = 'ValidationStory'
        self.work_item_url = ""
        self.ini_section_filter_feature = 'FilterFeature'
        self.default_validation_id = '2002986'
    def autoFillValidationStoryTasks(self):
        """
        @Function: To auto fill Validation Story & Four tasks
        @Parameter:
        @Returns:
        """
        #login and get the feature ids
        feature_ids = self.__login()
        #get the context from ini
        # validation_info = self.config.options('ValidationStory')
        context_validation_tasks = {}
        for section in self.config.sections():
            if section in self.tasks_section or section == self.ini_section_validation:
                section_data = {}
                for key, value in self.config.items(section):
                    section_data[key] = value
                context_validation_tasks[section] = section_data

        #for each feauture to get the information
        for feature_id in feature_ids:
            feature_info = self.__getFeatureInfo(feature_id) #(statueText, typeText, planForText, blockText, testableText, filedAgainstText, descriptionText, acceptanceCriteriaText)
            #check?
            dict_error = self.__checkFeatureInfo(feature_info)
            if dict_error:
                print('\033[31m' + "The feature {}'s information have some problems: ".format(feature_id) + '\033[0m')
                for key,value in dict_error.items():
                    print('\033[31m' + "\t {} - {}".format(key, value) + '\033[0m')
                # ask user if need to check or save
                continue_flag = input('\033[31m' + 'Do you need to continue build Validation Story & tasks for this feature {}: (Y/N)'.format(feature_id) + '\033[0m')
                if continue_flag.capitalize() == 'N':
                    print(
                        '\033[31m' + "The feature {} Not Done".format(feature_id) + '\033[0m')
                    continue
            #need to edit to an function to deal with featureInfo
            feature_info = self.__filterfeatureinfo(feature_id,feature_info)#featureid, planForText,filedAgainstText
            #validation story open -> create -> record -> close

            validation_id = self.__initValidationStory(feature_info, context_validation_tasks[self.ini_section_validation])
            # if validation_id == self.default_validation_id:
            #     print('Due to Not SAVE, the process will use story id:{} to continue to create the tasks'.format(self.default_validation_id))
            self.__closeCurrentPage()
            if not validation_id:
                continue
            #for each tasks open -> create -> record -> close
            taskids =[]
            for task in self.tasks_section:
                task_content = context_validation_tasks[task]
                self.__stayNewTask()
                taskid = self.__init_task(feature_info,validation_id,task_content)
                taskids.append(taskid)
                self.__closeCurrentPage()

            #input information
            print('The{} {} & {} have done'.format(feature_id, validation_id, taskids))

    def __initialization(self, file_path):
        """
        @Function: to initial the whole the program
        @Parameter: file_path -> the file of config.ini
        @Returns:
        """
        print('\033[31m' + "Since this is the first time you open this program, some initialization information needs to be added again. You can also add it in the Configuration folder\n. If you encounter any problems during use, please contact xingqiang.wang@stellantis.com\n" + '\033[0m')
        account = input('input Your account \n')
        password = input('input Your password \n')
        initialization = 'True'
        print('You can update the feature in the configuration->config.ini->FeatureList')
        print('You can update the CurrentTimeLine in the configuration->config.ini->FeatureList')
        DriverPath = input('input Your chrome Driver path \n')
        print('if you have any change on validation story or tasks, please change it on config.ini\n')


        if account and password and DriverPath:
            self.config['Identity']['Account'] = account
            self.config['Identity']['Password'] = password
            self.config['Identity']['Initialization'] = initialization
            self.config['URL']['DriverPath'] = DriverPath
            with open(file_path, 'w') as config_file:
                self.config.write(config_file)

    def __checkLoginInfo(self, account:str, password:str):
        """
        @Function: to check validation of the account & password
        @Parameter:
        @Returns: True or False
        """
        pattern_account = r'^[a-zA-Z]{1,2}\d+$'
        if not re.match(pattern_account, account):
            return False
        if len(password) != 8:
            return False
        return True

    def __login(self):
        """
        @Function: check the information of LoginConfig.ini
                   User need to confirm the Account, Password, FeatureIDList
        @Parameter:
        @Returns:
        """

        #get the information of LoginConfig.ini
        login_config_ini = os.path.join(self.base_dir, 'Resource', 'Configuration', 'Config.ini')
        # print(login_config_ini)
        if not (os.path.exists(login_config_ini) and os.path.isfile(login_config_ini)):
            print('*' * 10, 'LoginError--{:20s} invalid'.format("LoginConfig.ini's path"), '*' * 10)
            return
        self.config.read(login_config_ini)

        #check the vlaue of Initialization if True -> initialization else continue
        flag = bool(self.config.get('Identity', 'Initialization').lower() == 'false')
        if flag:
            self.__initialization(login_config_ini)

        #check the [Identity]
        account = self.config.get('Identity', 'Account')
        password = self.config.get('Identity', 'Password')
        if not self.__checkLoginInfo(account, password):
            print('*'*10, 'LoginError--{:20s} invalid'.format('account&password'), '*'*10)
            return

        #check the [Feature]
        feature_ids = self.config.get('Feature', 'FeatureList')
        if not self.__checkFeatureIDs(feature_ids):
            print('*' * 10, 'LoginError--{:20s} invalid'.format('featureID'), '*' * 10)
            return
        #check the [URL][DriverPath] and load
        driver_path = os.path.join(self.base_dir, 'Resource', 'Driver', 'chromedriver.exe')
        if not (os.path.exists(driver_path) and os.path.isfile(driver_path)):
            print('*' * 10, 'LoginError--{:20s} invalid'.format("chromedriver's path"), '*' * 10)
            return

        #login by [Identity] into SWXSmartCockpitDashboards
        self.driver = self.__getDriver(driver_path)
        self.driver.get(self.config.get('URL', 'SWXSmartCockpitDashboards'))
        WebDriverWait(self.driver, self.timeout, self.poll_frequency).until(
            EC.presence_of_element_located((By.ID, '''jazz_app_internal_LoginWidget_0_password''')))
        self.driver.find_element(By.ID, 'jazz_app_internal_LoginWidget_0_userId').send_keys(account)
        self.driver.find_element(By.ID, 'jazz_app_internal_LoginWidget_0_password').send_keys(password)
        self.driver.find_element(By.XPATH, '//button[@type = "submit"]').click()
        #get the CurrentTimeLine
        self.current_time_line = self.config.get('Feature', 'CurrentTimeLine')
        #get the FeatureTemplate
        self.feature_template = self.config.get('URL', 'FeatureTemplate')
        #get the work item
        self.work_item_url = self.config.get('URL', 'WorkItemUrl')
        
        #return the FeatureIDs
        return self.config.get('Feature', 'FeatureList').split(',')



    def __getFeatureInfo(self, id):
        """
        @Function: get relate feature information
        @Parameter: id -> feature id
        @Returns: feature information
        """
        featureURL = self.feature_template.format(id)
        self.driver.execute_script('window.open()')
        self.driver.switch_to.window(self.driver.window_handles[-1])
        self.driver.get(featureURL)
        WebDriverWait(self.driver, 180, 1).until(EC.presence_of_element_located(
            (By.XPATH, '''//*[@id="com_ibm_team_rtc_foundation_web_ui_views_DecoratedRadioButton_3_input"]''')))
        #to get the relate feature information
        #to get the statue text
        selectStatue = self.driver.find_element(By.XPATH,
                                           '''//*[@id="com_ibm_team_workitem_web_ui_internal_view_editor_parts_StatusAttributePart_0"]/div/select''')
        statueText = Select(selectStatue).first_selected_option.text
        #to get the type text
        typeText = self.driver.find_element(By.XPATH,
                                       '''//*[@id="com_ibm_team_workitem_web_mvvm_view_queryable_combo_QueryableComboView_0"]/div[2]/span[2]''').text
        #to get the PlanFor text
        planForText = self.driver.find_element(By.XPATH,
                                          '''//*[@id="com_ibm_team_workitem_web_mvvm_view_queryable_combo_QueryableComboView_1"]/div[2]/span[2]''').text
        #to get the block statue text
        blockText = None
        for blocktype in range(1, 4):
            radioBlockType = self.driver.find_element(By.XPATH,
                                                 '''//*[@id="com_ibm_team_rtc_foundation_web_ui_views_DecoratedRadioButton_{}_input"]'''.format(
                                                     blocktype))
            if radioBlockType.is_selected():
                blockText = ["Unassigned", "Yes", "No"][blocktype - 1]
                break
        #to get the testable text
        testableText = self.driver.find_element(By.XPATH,
                                           '''//table[@summary = "Second details group"]/tbody/tr[7]/td/div/div[2]/span[2]''').text
        #to get the filedAgainst text
        filedAgainstText = self.driver.find_element(By.XPATH,
                                               '''//table[@class = 'DetailsInnerTable']/tbody/tr/td/div/div[2]/div/div/span[2]''').text
        #to get the description text
        descriptionText = self.driver.find_element(By.XPATH,
                                              '''//div[@class = "LeftColumn"]/div[5]/div[@class = "SectionWithoutBorder"]/div/div[3]/div/div/div[2]''').text
        #to get the acceptance Criteria text
        acceptanceCriteriaText = self.driver.find_element(By.XPATH,
                                                '''//div[@class = "LeftColumn"]/div[6]/div[@class = "SectionWithoutBorder"]/div/div[3]/div/div/div[2]''').text
        self.__closeCurrentPage()
        return (statueText, typeText, planForText, blockText, testableText, filedAgainstText, descriptionText,
                acceptanceCriteriaText)

    def __openValidationStory(self):
        """
        @Function: open the validation story page
        @Parameter:
        @Returns:
        """
        self.driver.execute_script('window.open()')
        self.driver.switch_to.window(self.driver.window_handles[-1])
        self.driver.get(self.work_item_url)
        WebDriverWait(self.driver, 180, 1).until(EC.presence_of_element_located((By.XPATH,
                                                                            '''//*[@id="com_ibm_team_workitem_web_ui_internal_page_WorkItemWelcomePage2_0"]/div[2]/div[2]/div[3]/div[2]/div[1]/a''')))
        self.driver.find_element(By.XPATH,
                            '''//*[@id="com_ibm_team_workitem_web_ui_internal_page_WorkItemWelcomePage2_0"]/div[2]/div[2]/div[3]/div[2]/div[1]/a''').click()
        WebDriverWait(self.driver, 120, 0.5).until(EC.presence_of_element_located((By.XPATH,
                                                                              '''//*[@id="com_ibm_team_workitem_web_ui_internal_view_layout_SectionLayout_0"]/div/div/div[3]/div/div/table/tbody/tr/td[1]/div/table/tbody/tr[1]/td''')))
        self.driver.find_element(By.XPATH,
                            '''//*[@id="com_ibm_team_workitem_web_ui_internal_view_layout_SectionLayout_0"]/div/div/div[3]/div/div/table/tbody/tr/td[1]/div/table/tbody/tr[1]/td''').click()
        WebDriverWait(self.driver, 120, 0.5).until(EC.presence_of_element_located((By.XPATH,
                                                                              '''//*[@id="com_ibm_team_workitem_web_mvvm_view_queryable_combo_QueryableSection_0"]/ul/li[6]''')))
        self.driver.find_element(By.XPATH,
                            '''//*[@id="com_ibm_team_workitem_web_mvvm_view_queryable_combo_QueryableSection_0"]/ul/li[6]''').click()
        WebDriverWait(self.driver, 120, 0.5).until_not(EC.presence_of_element_located((By.XPATH,
                                                                                  '''//span[@class = 'floatingTable']/span[@class = 'titleTextArea']/span[@class = 'TitleText' and starts-with(@aria-label, 'Epic <') and starts-with(text(), 'Epic <')]''')))

    def __initValidationStory(self, feature_info, validation_story_info):
        """
        @Function: to create the validation story
        @Parameter: feature_info -> the information of feature, validation_story_info -> the information of validation story
        @Returns: the new validation story id
        """
        self.__openValidationStory()

        # type Summary
        summary = validation_story_info['summary'].format(feature_info[2], feature_info[0])
        self.driver.find_element(By.XPATH,
                            '''//div[@dojoattachpoint = '_workItemEditorContainer']/div/div[2]/div/div[3]/div[2]/div/div/div[2]''').send_keys(
            summary)
        # type Description
        self.driver.find_element(By.CSS_SELECTOR,
                            'div[dojoattachpoint="_editorAttachPoint"][aria-label="Description"]').send_keys(
            validation_story_info['description'].format(feature_info[2], feature_info[0]))
        #
        # type Filed Against
        self.driver.find_element(By.XPATH, '''//tr[@class = 'LabelValueTableRow']/td/div/div[2]/div/div/span[3]''').click()
        time.sleep(1)
        filedagainstElement = WebDriverWait(self.driver, 120, 0.5).until(
            EC.presence_of_element_located((By.XPATH, '''//span[contains(text(), '{}')]'''.format(validation_story_info['filedagainst']))))
        filedagainstElement.click()

        # type Owned By
        self.driver.find_elements(By.XPATH,
                             '''//table[@class = 'DetailsInnerTable' and @summary = 'Second details group']/tbody/tr/td/div/div[2]/span[3]''')[
            0].click()
        ownedbyElement = WebDriverWait(self.driver, 120, 0.5).until(
            EC.presence_of_element_located((By.XPATH, '''/html/body/div[9]/div[1]/input''')))
        ownedbyElement.send_keys(validation_story_info['ownedby'])
        ownedby_element = WebDriverWait(self.driver, 120, 0.5).until(
            EC.presence_of_element_located((By.XPATH, '''//span[contains(text(), '{}') and @class = 'Highlight']'''.format(validation_story_info['ownedby']))))
        ownedby_element.click()
        self.driver.find_elements(By.XPATH,
                             '''//table[@class = 'DetailsInnerTable' and @summary = 'First details group']/tbody/tr/td/div/div/span[3]''')[
            1].click()
        planFor_element = WebDriverWait(self.driver, 120, 0.5).until(
            EC.presence_of_element_located((By.XPATH, '/html/body/div[9]/div[1]/input')))
        planFor_element.send_keys(feature_info[1])
        planFor_element_2 = WebDriverWait(self.driver, 120, 0.5).until(
            EC.presence_of_element_located((By.XPATH,
                                            '''//span[contains(text(), '{}') and @class = 'Highlight']'''.format(
                                                feature_info[1]))))
        planFor_element_2.click()
        # click set related button
        self.driver.find_elements(By.XPATH,
                             '''//div[@class = 'SectionInnerBorder SectionInnerBorderTop']/div[3]/div/div/div/div/div[2]/span[2]''')[
            0].click()
        self.driver.find_element(By.ID, '''dijit_MenuItem_67_text''').click()
        #
        # # tpye featureID
        tpye_feature_id = WebDriverWait(self.driver, 120, 0.5).until(
            EC.presence_of_element_located((By.XPATH, '''//*[@id="com_ibm_team_workitem_web_ui_internal_view_editor_SelectWorkItemContent_0"]/div/div[3]/div[2]/div/input''')))
        tpye_feature_id.send_keys(feature_info[0])
        tpye_feature_id.send_keys(Keys.ENTER)
        WebDriverWait(self.driver, 60, 0.5).until(EC.visibility_of_element_located(
            (By.XPATH, '''//option[starts-with(text(), '{}')]'''.format(feature_info[0])))).click()
        WebDriverWait(self.driver,120, 0.5).until(EC.element_to_be_clickable((By.XPATH, '''//button[@class = 'j-button-primary' and contains(text(), 'OK')]'''))).click()

        # self.driver.find_element(By.XPATH, '''//button[contains(text(), 'OK') and @class = 'j-button-primary']''').click()
        # click save button
        try:
            WebDriverWait(self.driver, 120, 0.5).until(EC.element_to_be_clickable((By.XPATH,
                                                                                   '''//*[@id="com_ibm_team_workitem_web_ui_internal_view_editor_WorkItemEditorHeader_0"]/div[1]/span/span[3]/span/button[2]'''))).click()
        except ElementClickInterceptedException:
            input('There is some question about the Save button, please resolve it by manually')
        # self.driver.find_element(By.XPATH,
        #                     '''//*[@id="com_ibm_team_workitem_web_ui_internal_view_editor_WorkItemEditorHeader_0"]/div[1]/span/span[3]/span/button[2]''').click()
        # time.sleep(5)
        # get validation story ID
        validationStr = WebDriverWait(self.driver, 120, 0.5).until(EC.presence_of_element_located(
            (By.XPATH, '''//span[contains(text(), 'Validation ') and @class = 'TitleText' and not( contains(text(), ' <'))] '''))).text
        validationID = re.findall(r'\d+', validationStr)
        if len(validationID[0]) != 7:
            print(
                '\033[31m' + 'There is an issue when process try to create the validation Story, feature id:{}'.format(
                    feature_info[0]) + '\033[0m')
            exit_flag = input('Press "q" to exit the process')
            if exit_flag == 'q':
                return None
        time.sleep(5)
        # get validation story ID
        validationStr = WebDriverWait(self.driver, 120, 0.5).until(EC.presence_of_element_located(
            (By.XPATH, '''//span[contains(text(), 'Validation ') and @class = 'TitleText']'''))).text
        validationID = re.findall(r'\d+', validationStr)
        return validationID[0]



    def __closeCurrentPage(self):
        """
        @Function: close the current page
        @Parameter:
        @Returns:
        """
        self.driver.close()
        self.driver.switch_to.window(self.driver.window_handles[0])

    def __checkFeatureIDs(self, param:str):
        """
        @Function: to check the feature list
        @Parameter: param -> features string
        @Returns:
        """
        pattern_param = r'^\d{7}(,\d{7})*$'
        if not re.match(pattern_param, param):
            return False
        return True

    def __getDriver(self, filePath):
        """
        @Function: get Driver
        @Parameter: filePath: the Path of Driver
        @Returns:driver object
        """
        options = webdriver.ChromeOptions()
        prefs = {
            'profile.default_content_setting_values':
                {
                    'notifications': 2
                }
        }
        options.add_experimental_option('prefs', prefs)  # 关掉浏览器左上角的通知提示
        options.add_argument("disable-infobars")  # 关闭'chrome正受到自动测试软件的控制'提示

        return webdriver.Chrome(service=Service(filePath), options=options)

    def __checkFeatureInfo(self, info):
        """
        @Function: to check the information of feature
        @Parameter:info -> the information of feature
        @Returns:dict_error
        """
        dict_error = {}
        return dict_error
    def __filterfeatureinfo(self, feature_id:str, feature_info:list):
        """
        @Function: filter feature information to get the new information
        @Parameter: feature_id -> feature's id, feature_info -> feature information
        #(statueText, typeText, planForText, blockText, testableText, filedAgainstText, descriptionText, acceptanceCriteriaText)
        @Returns: new feature_info
        """
        feature_new_info = []
        feature_new_info.append(feature_id)
        if feature_info[2] == 'Backlog':
            feature_new_info.append(feature_info[2])
        else:
            feature_year, feature_value = self.__parse_string(feature_info[2])
            current_year, current_value = self.__parse_string(self.current_time_line)
            if feature_year > current_year:
                feature_new_info.append(feature_info[2])
            elif current_year > feature_year:
                feature_new_info.append(self.current_time_line)
            else:
                if feature_value >= current_value:
                    feature_new_info.append(feature_info[2])
                else:
                    feature_new_info.append(self.current_time_line)



        for section in self.config.sections(): #filedAgainstText
            if section == self.ini_section_filter_feature:
                is_flag = False
                for key, value in self.config.items(section):
                    if key == feature_info[5].lower():
                        feature_new_info.append(value)
                        is_flag = True
                if not is_flag:
                    feature_new_info.append(feature_info[5])
                    pass
        return feature_new_info#featureid, planForText,filedAgainstText


    def __parse_string(self, string_pi):
        """
        @Function:# 解析字符串，提取数字和浮点数部分
        @Parameter:string_pi -> current PI
        @Returns:year, value
        """
        match = re.match(r'(\d+)\s*PI\s*([\d.]+)', string_pi)
        if match:
            year = int(match.group(1))
            value = float(match.group(2))
            return year, value
        return None

    def __stayNewTask(self):
        self.driver.execute_script('window.open()')
        self.driver.switch_to.window(self.driver.window_handles[-1])
        self.driver.get(self.work_item_url)
        # # click 'Create a work item'
        WebDriverWait(self.driver, 120, 0.5).until(EC.presence_of_element_located((By.XPATH,
                                                                              '''//*[@id="com_ibm_team_workitem_web_ui_internal_page_WorkItemWelcomePage2_0"]/div[2]/div[2]/div[3]/div[2]/div[1]/a'''))).click()
        # click Epic
        WebDriverWait(self.driver, 120, 0.5).until(EC.presence_of_element_located((By.XPATH,
                                                                              '''//*[@id="com_ibm_team_workitem_web_ui_internal_view_layout_SectionLayout_0"]/div/div/div[3]/div/div/table/tbody/tr/td[1]/div/table/tbody/tr[1]/td'''))).click()
        WebDriverWait(self.driver, 120, 0.5).until(EC.presence_of_element_located((By.XPATH,
                                                                              '''//*[@id="com_ibm_team_workitem_web_mvvm_view_queryable_combo_QueryableSection_0"]/ul/li[5]'''))).click()
        WebDriverWait(self.driver, 120, 0.5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-placeholder = 'Add a comment...']")))
        WebDriverWait(self.driver, 120, 0.5).until_not(EC.presence_of_element_located((By.XPATH,
                                                                                  '''//span[@class = 'floatingTable']/span[@class = 'titleTextArea']/span[@class = 'TitleText' and starts-with(@aria-label, 'Epic <') and starts-with(text(), 'Epic <')]''')))

    def __init_task(self, feature_info, validation_id, task_content):
        # type Summary
        summary = task_content['summary'].format(feature_info[-1], feature_info[0])
        self.driver.find_element(By.XPATH,
                            '''//div[@dojoattachpoint = '_workItemEditorContainer']/div/div[2]/div/div[3]/div[2]/div/div/div[2]''').send_keys(
            summary)
        # type Priority
        self.driver.find_elements(By.XPATH,
                             '''//span[contains(string(), 'Priority: ')]/../following-sibling::td/div/div[2]/span[2]''')[
            -1].click()
        WebDriverWait(self.driver, 120, 0.5).until(EC.visibility_of_element_located(
            (By.XPATH, '''//span[contains(text(), '{}')]'''.format(task_content['priority'])))).click()

        # type Planned for
        self.driver.find_elements(By.XPATH,
                             '''//span[contains(string(), 'Planned For: ')]/../following-sibling::td/div/div[2]/span[2]''')[
            -1].click()
        WebDriverWait(self.driver, 120, 0.5).until(EC.visibility_of_element_located(
            (By.XPATH, '''/html/body/div/div[@class = 'SearchBox']/input'''))).send_keys(feature_info[1])
        WebDriverWait(self.driver, 120, 0.5).until(EC.visibility_of_element_located(
            (By.XPATH, '''//span[contains(text(), '{}')]'''.format(feature_info[1])))).click()

        # type Filed Against
        self.driver.find_elements(By.XPATH,
                             '''//span[contains(string(), 'Filed Against: ')]/../following-sibling::td/div/div[2]/div''')[
            -1].click()
        WebDriverWait(self.driver, 120, 0.5).until(EC.visibility_of_element_located(
            (By.XPATH, '''/html/body/div/div[@class = 'SearchBox']/input'''))).send_keys(task_content['filedagainst'])
        time.sleep(2)
        WebDriverWait(self.driver, 120, 0.5).until(EC.visibility_of_element_located(
            (By.XPATH, '''//span[contains(text(), '{}')]'''.format(task_content['filedagainst'])))).click()

        # type Owned By
        self.driver.find_elements(By.XPATH,
                             '''//span[contains(string(), 'Owned By: ')]/../following-sibling::td/div/div[2]''')[
            -1].click()
        WebDriverWait(self.driver, 120, 0.5).until(EC.visibility_of_element_located(
            (By.XPATH, '''/html/body/div/div[@class = 'SearchBox']/input'''))).send_keys(task_content['ownedby'])
        time.sleep(1)
        WebDriverWait(self.driver, 120, 0.5).until(EC.visibility_of_element_located(
            (By.XPATH, '''//span[contains(text(), '{}') and  @class = 'Highlight']'''.format(task_content['ownedby'])))).click()

        # type Description
        self.driver.find_elements(By.CSS_SELECTOR, '''div[aria-label = 'Description']''')[-1].send_keys(task_content['description'].format(feature_info[0]))

        # click set related button
        self.driver.find_elements(By.XPATH,
                             '''//div[@class = 'SectionInnerBorder SectionInnerBorderTop']/div[3]/div/div/div/div/div[2]/span[2]''')[
            0].click()
        self.driver.find_element(By.ID, '''dijit_MenuItem_67_text''').click()
        WebDriverWait(self.driver, 180, 0.5).until(EC.visibility_of_element_located((By.XPATH,
                                                                                '''//div[contains(text(), 'Work Item Number or Words Contained in the Text. Use quotes for a phrase search:')]/following-sibling::div/div/input'''))).click()
        # tpye validation id
        time.sleep(2)
        self.driver.find_element(By.XPATH, '''//div[contains(text(), 'Work Item Number or Words Contained in the Text. Use quotes for a phrase search:')]/following-sibling::div/div/input''').send_keys(validation_id)
        self.driver.find_element(By.XPATH, '''//div[contains(text(), 'Work Item Number or Words Contained in the Text. Use quotes for a phrase search:')]/following-sibling::div/div/input''').send_keys(Keys.ENTER)
        time.sleep(2)

        #select validation id and click OK button
        time.sleep(2)
        WebDriverWait(self.driver,120, 0.5).until(EC.visibility_of_element_located((By.XPATH, '''//option[@value = '{}']'''.format(validation_id)))).click()
        WebDriverWait(self.driver,120, 0.5).until(EC.element_to_be_clickable((By.XPATH, '''//button[@class = 'j-button-primary' and contains(text(), 'OK')]'''))).click()

        # self.driver.find_element(By.XPATH, '''//*[@id="jazz_ui_Dialog_0"]/div[3]/div/button[2]''').click()

        # todo: cancel it
        # click save
        try:
            WebDriverWait(self.driver,120,0.5).until(EC.element_to_be_clickable((By.XPATH,  '''//*[@id="com_ibm_team_workitem_web_ui_internal_view_editor_WorkItemEditorHeader_0"]/div[1]/span/span[3]/span/button[2]'''))).click()
        except ElementClickInterceptedException:
            input('There is some question about the Save button, please resolve it by manually')
        # self.driver.find_element(By.XPATH,
        #                     '''//*[@id="com_ibm_team_workitem_web_ui_internal_view_editor_WorkItemEditorHeader_0"]/div[1]/span/span[3]/span/button[2]''').click()
        # # time.sleep(5)
        # get validation story ID
        taskStr = WebDriverWait(self.driver, 120, 0.5).until(EC.presence_of_element_located(
            (By.XPATH, '''//span[contains(text(), 'Task ') and @class = 'TitleText' and not( contains(text(), ' <'))] '''))).text
        task_id = re.findall(r'\d+', taskStr)
        if len(task_id[0]) != 7:
            print(
                '\033[31m' + 'There is an issue when process try to create the task-{}, feature id:{}'.format(summary,
                    feature_info[0]) + '\033[0m')
            exit_flag = input('Press "q" to exit the process')
            if exit_flag == 'q':
                return None

        return task_id[0]
if __name__ == '__main__':
    AutoRQM().autoFillValidationStoryTasks()