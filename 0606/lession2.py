import requests
from requests import Response

# 主程式：負責下載 YouBike 即時資料並檢查結果
def main():
    # API 網址（回傳 JSON 格式資料）
    url:str = "https://tcgbusfs.blob.core.windows.net/dotapp/youbike/v2/youbike_immediate.json"

    # 發送 HTTP GET 請求，取得伺服器回應
    response:Response = requests.get(url)

    # 顯示 response 的型別，讓初學者知道回傳的是 Response 物件
    print(type(response))

    # status_code == 200 代表請求成功
    if response.status_code == 200:
        # 把回應內容（JSON）轉成 Python 的 list/dict 結構
        data:list[dict] = response.json()
        print("下載成功")

        # 觀察下載後資料的基本資訊
        print(type(data))
        print(len(data))

        # 印出第一筆資料，方便了解每一筆資料欄位長怎樣
        print(data[0])
    else:
        # 請求失敗時，印出狀態碼協助除錯
        print("下載失敗")
        print(response.status_code)

# 只有直接執行這個檔案時才會呼叫 main()
if __name__ == '__main__':
    main()