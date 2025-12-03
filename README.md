## 1. 自動化 S3 檔案上傳系統 (s3test.py)

### 目標

* 檢查 S3 Bucket 是否存在。
* 不存在則自動建立。
* 支援上傳任意本機檔案至 S3。
* 適合作為後端備份/檔案管理 Automation 基礎。

### 部署要素

| 服務 | 說明 |
| :--- | :--- |
| **S3 Bucket** | 檢查並自動建立。 |
| **檔案** | 支援上傳任意本地檔案。 |

---

## 2. 自動化 AWS 網站部署 Pipeline (foliosetupaws.py)

### 目標

使用 Python + Boto3 自動部署完整 Web 架構。

### 部署流程 (自動化 Web 架構)

* **Key Pair 建立/檢查**
* **Security Group 自動管理**
* **EC2 Instance 自動部署**
* **User Data** 自動安裝 Web server + 導入網站模板
* **Application Load Balancer (ALB)** 設定
* **Target Group** 自動綁定 EC2
* 完整部署後可直接透過 **ALB** 進入網站
