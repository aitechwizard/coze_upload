import time
import os
import sys

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

import config


# 数组切割
def chunked_list(input_list, size):
    for i in range(0, len(input_list), size):
        yield input_list[i:i + size]


def filter_had_upload_file(ready_upload_files, had_upload_files):
    need_upload_files = []
    for file in ready_upload_files:
        if file in had_upload_files:
            continue
        exist = False
        for had_upload_file in had_upload_files:
            if had_upload_file in file:
                exist = True
                break
        if exist:
            continue
        need_upload_files.append(file)
    return need_upload_files


# file_path 需要替换为你的文件夹路径
file_dir = config.UPLOAD_FILE_DIR
if not os.path.exists(file_dir):
    print('file dir does not exist', file_dir)
    sys.exit(1)

print('file_dir: ', file_dir)

# 获取文件夹的文件列表，注意这里不会获取子文件夹的文件，需要的话自行修改
entries = os.listdir(file_dir)

# 支持的文件后缀
ext_list = ['.txt', '.pdf', '.doc', '.docx']

files = []
for entry in entries:
    full_path = os.path.join(file_dir, entry)
    if os.path.isfile(full_path):
        for ext in ext_list:
            if entry.endswith(ext) and os.path.getsize(full_path) > 0:
                files.append(full_path)

if len(files) == 0:
    print('no file found')
    sys.exit()

if not config.SKIP_MAX_UNIT_SIZE and len(files) > 100:
    print('Coze每个知识库只支持100个unit，也就是100个文件')
    sys.exit()

# 保存chrome的数据，不然每次都需要登录
user_data_dir = config.CHROME_DATA_PATH
chrome_options = Options()
chrome_options.add_argument(f'--user-data-dir={user_data_dir}')
driver = webdriver.Chrome(service=Service(), options=chrome_options)

print('open chrome driver===')

# 如果每次都要创建一个新的 Chrome 会话，使用这个方法
# driver = webdriver.Chrome()

# 知识库的页面路径
know_page = config.COZE_KNOW_PAGE

# Coze 每次只能上传10个文件
chunk_size = config.COZE_TXT_UPLOAD_MAX_SIZE
if chunk_size > 10:
    chunk_size = 10

# 上传失败的文件（目前并没有做到识别某个具体的文件上传失败，而是这个批次只要失败了就会都放到失败列表）
success_upload_files = []
fail_upload_files = []
for index, file_chunk in enumerate(chunked_list(files, chunk_size), start=1):
    # 过滤之前已经上传过的文件列表
    need_upload_files = filter_had_upload_file(file_chunk, config.HAD_UPLOAD_FILE_PATH)
    if len(need_upload_files) == 0:
        print("all filter")
        continue
    try:
        # 打开Coze知识库的主页
        driver.get(know_page)

        # 最多休眠10秒等待页面加载完成，如果网速太慢，可适当延长这个时间
        add_unit_wait = WebDriverWait(driver, 10)
        # 点击 Add unit 按钮
        add_unit_btn_xpath = '//*[@id="root"]/div[2]/section/section/main/div/div/div[2]/div[2]/button'
        add_unit_btn = add_unit_wait.until(EC.presence_of_element_located((By.XPATH, add_unit_btn_xpath)))
        add_unit_btn.click()

        # 等待5秒
        time.sleep(3)

        # 点击 Next 按钮
        next_btn = driver.find_element(by=By.XPATH, value='//*[@id="dialog-0"]/div/div[3]/button[2]')
        next_btn.click()

        # 等待文件上传输入元素加载完成
        wait = WebDriverWait(driver, 5)
        # 通过 send_keys 方法发送多个文件路径，实现多文件选择和上传
        for file in need_upload_files:
            file_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']")))
            file_input.send_keys(file)

        time.sleep(3)

        # 点击Next按钮(Upload节点的)
        upload_next_btn_xpath = '//*[@id="root"]/div[2]/section/section/main/div/div/div[2]/div/div/div[4]/button'
        upload_next_btn = driver.find_element(by=By.XPATH, value=upload_next_btn_xpath)
        upload_next_btn.click()

        time.sleep(3)

        # 点击Next按钮(Segmentation节点的)
        segment_next_btn_xpath = '//*[@id="root"]/div[2]/section/section/main/div/div/div[2]/div/div/div[3]/button[2]'
        segment_next_btn = driver.find_element(by=By.XPATH, value=segment_next_btn_xpath)
        segment_next_btn.click()

        # 确认上传按钮
        confirm_wait = WebDriverWait(driver, 10)
        confirm_btn_xpath = '//*[@id="root"]/div[2]/section/section/main/div/div/div[2]/div/div/div[3]/button'
        confirm_btn = confirm_wait.until(EC.presence_of_element_located((By.XPATH, confirm_btn_xpath)))
        confirm_btn.click()

        success_upload_files.extend(file_chunk)
        if len(success_upload_files) >= 100:
            print('over max size, exit')
            sys.exit()

        time.sleep(5)
    except Exception as e:
        print('upload failed', file_chunk, e)
        fail_upload_files.extend(file_chunk)

print('fail upload files number', len(fail_upload_files))
print('fail upload files', fail_upload_files)

# 关闭浏览器
driver.quit()
