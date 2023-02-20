### GCP 建立虛擬機器腳本
這是一個用於在 GCP 上建立多台虛擬機器的 Python 腳本。您可以使用這個腳本輕鬆地建立多台具有自定義啟動腳本的虛擬機器。

### 如何使用
這個腳本需要使用 gcloud 工具，所以在使用之前，請確保您已經安裝了這個工具。

在命令列中使用以下指令來建立虛擬機器：
```
python create_gcp_vms.py --start <start_number> --end <end_number> --script <startup_script> --project <project_id> --zone <zone> --image-project <image_project> --image-family <image_family> --name-prefix <name_prefix>
```

### 這些參數的意思如下：
start: 起始虛擬機器的編號。預設值為 1。
end: 結束虛擬機器的編號。預設值為 2。
script: 虛擬機器的啟動腳本。預設為一個安裝 Docker 和 Ray 庫的腳本。
project: 您的 GCP 專案 ID。預設為 plant-hero。
zone: 虛擬機器所在的區域。預設為 us-central1-a。
image-project: 用於建立虛擬機器的映像的專案 ID。預設為 debian-cloud。
image-family: 用於建立虛擬機器的映像的系列。預設為 debian-11。
name-prefix: 虛擬機器名稱的前綴。預設為 vm-。

### 範例
以下範例會建立 3 台虛擬機器，使用自定義啟動腳本：
```
python create_gcp_vms.py --start 1 --end 3 --script "#!/bin/bash
touch test.txt"
```

### 撰寫此程式曾遇過的困難與突破
* Google Cloud Platform 對於性價比最好的 VM t2d-standard-1 類型有限制
* 每個月 t2d-standard-1 Spot VM 5.05 USD 一個專案最多 24 個VM，請求提高 700 之後，Google 實際給了上限 500 個 VM
* 一開始不知道為何無法通 port 80 443 後來才知道要加入 network tags https_server http_server 卡很久
* 一開始不知道如何預設安裝 docker 後來才發現 startup_script 可以完成任何安裝 VM 之後想做的事情
* 一開始無法同時啟動多個 VM 後來才改用 threading 解決，避免一個卡一個啟動很慢
* 採用 ChatGPT 協助 CLI 參數化設計
* 一開始 ChatGPT 總是給老舊錯誤的程式碼，作者去抓了最新的 GCP API 教會 ChatGPT 之後再寫
* 要小步前進，不可以一開始就 ChatGPT 設計整個大架構，要一個一個函式測試能跑才擴增，不然除錯會很困難

### todo
* 要把啟動的 VM 輸出為 json 公告 Public IP, Private IP 給呼叫方運用
* 寫為 python package 用 pip install 就能安裝
