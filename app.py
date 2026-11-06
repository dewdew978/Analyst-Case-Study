from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title='FruitBlend24',layout='wide')
folder=Path(__file__).with_name('app_data')
CSV_FILES=['pnl','kitchens','menus','promotions','forecast','inventory','hourly','summary','duplicate_sensitivity','scenario_sensitivity']
if not all((folder/f'{name}.csv').exists() for name in CSV_FILES):
    st.info('รัน analysis.ipynb ให้ครบก่อน เพื่อสร้าง CSV ใน app_data')
    st.stop()

@st.cache_data
def load_data(folder, modified):
    r={name:pd.read_csv(Path(folder)/f'{name}.csv',encoding='utf-8-sig') for name in CSV_FILES}
    for name in ['pnl','menus','forecast','inventory']:
        r[name]['month']=pd.to_datetime(r[name]['month'])
    monthly=r.pop('menus')
    r['monthly_demand']=monthly[['month','sku','units','days']].copy()
    r['monthly_demand']['cups_per_day']=monthly['units']/monthly['days']
    r['menu']=monthly.groupby('sku',as_index=False)[['units','revenue','profit_before_waste','waste_cost']].sum()
    r['menu']['contribution']=r['menu']['profit_before_waste']-r['menu']['waste_cost']
    r['menu']['profit_per_cup']=r['menu']['contribution']/r['menu']['units']
    r['prices']=monthly.loc[monthly['month'].eq(monthly['month'].max())].copy()
    prices=r['prices']
    prices['avg_price']=prices['revenue']/prices['units']
    prices['variable_cost']=prices[['fruit','pack','labor']].sum(axis=1)/prices['units']
    prices['waste_per_cup']=prices['waste_cost']/prices['units']
    prices['profit_per_cup']=(prices['profit_before_waste']-prices['waste_cost'])/prices['units']
    fees=r['promotions'].groupby('platform_name')['commission_rate'].first()
    prices['break_even_LM']=(prices['variable_cost']+prices['waste_per_cup'])/(1-fees['LINE MAN'])
    prices['break_even_Grab']=(prices['variable_cost']+prices['waste_per_cup'])/(1-fees['Grab'])
    history_names={'actual_days':'active_days','actual_units':'units','actual_revenue':'revenue','actual_profit_before_waste':'profit_before_waste','actual_profit_per_cup':'profit_per_cup'}
    r['promo_history']=r['promotions'][['sku','platform_name','rate_code_name']+list(history_names)].rename(columns=history_names)
    r['promo_check']=r['promotions'].dropna(subset=['model_selling_price']).rename(columns={'model_selling_price':'selling_price','model_profit_before_waste':'profit_before_waste','model_profit_after_waste':'profit_after_waste'})
    detail=r['inventory']
    r['inventory']=detail.groupby(['month','sku'],as_index=False)[['forecast_units','prepared_cups','waste_cups','fruit_value_thb']].sum()
    plan=detail.loc[detail['month'].eq(detail['month'].min()),['kitchen','sku','prepared_cups','days']].copy()
    plan['daily_need']=plan['prepared_cups']/plan['days']
    plan['target_cups']=(plan['daily_need']*2.5).apply(__import__('math').ceil)
    plan['on_hand'],plan['on_order']=0,0
    plan['order_cups']=plan['target_cups']
    r['order_plan']=plan[['kitchen','sku','daily_need','target_cups','on_hand','on_order','order_cups']]
    notes=r.pop('summary')
    r['quality']=notes.loc[notes['section'].eq('quality'),['item','value']].rename(columns={'item':'ปัญหา','value':'จำนวน'})
    r['quality']['จำนวน']=pd.to_numeric(r['quality']['จำนวน'])
    r['waste_estimates']=notes.loc[notes['section'].eq('estimated_waste'),['item','value','units_wasted','est_waste_cost_thb','reference_days','waste_estimated']].rename(columns={'item':'date','value':'kitchen / sku'})
    r['waste_adjustment']=float(notes.loc[notes['section'].eq('waste_adjustment'),'value'].item())
    validation=notes.loc[notes['section'].eq('validation')].set_index('item')['value']
    r['validation_errors']=[float(validation['one_month']),float(validation['three_months'])]
    r['weekly_wape'],r['fixed_wape']=float(validation['rolling_weekly']),float(validation['fixed_origins'])
    r['weekly_backtest']=notes.loc[notes['section'].eq('weekly_backtest'),['item','fixed_wape_pct','weekly_wape_pct']].rename(columns={'item':'วันตัดข้อมูล','fixed_wape_pct':'WAPE ตรึงแผน 3 เดือน (%)','weekly_wape_pct':'WAPE อัปเดตทุกสัปดาห์ (%)'})
    r['forecast_as_of']=pd.Timestamp(notes.loc[notes['section'].eq('as_of'),'value'].item())
    r['next_review']=pd.Timestamp(notes.loc[notes['section'].eq('forecast_method') & notes['item'].eq('next_review'),'value'].item())
    return r

r=load_data(str(folder),tuple((folder/f'{name}.csv').stat().st_mtime_ns for name in CSV_FILES))
# ข้อค้นพบคำนวณจากตารางล่าสุด ส่วนคำอธิบายอ่านจากรายงาน
worst=r['kitchens'].sort_values('operating_profit').iloc[0]
berry=r['menu'].loc[r['menu']['sku'].eq('MixedBerryPremium')].iloc[0]
scenario_totals=r['forecast'].groupby('scenario')['operating_profit'].sum()
trial_before_saving=r['forecast'].loc[r['forecast']['scenario'].eq('แผนทดลอง'),'profit_before_savings'].sum()
central_case=r['scenario_sensitivity'].loc[r['scenario_sensitivity']['berry_demand_drop_pct'].eq(20)].set_index(['waste_reduction_pct','monthly_overhead_saving'])['operating_profit_3m']
plan_bridge=pd.DataFrame({'case':['ฐาน: ดำเนินต่อแบบเดิม','ทดลองราคา: ของเสียและ overhead เดิม','เพิ่มการลดอัตราของเสีย 50%','เพิ่มการประหยัด overhead 30,000 บาท/เดือน'],
    'operating_profit_3m':[scenario_totals['ฐาน'],central_case.loc[(0,0)],central_case.loc[(50,0)],central_case.loc[(50,30000)]]})

r['insights']=[
    f"รายได้ {r['pnl']['gross_revenue_thb'].sum():,.2f} บาท แต่ขาดทุนตามต้นทุนที่บันทึก/ประมาณ {abs(r['pnl']['operating_profit'].sum()):,.2f} บาท และขาดทุน {r['pnl']['operating_profit'].lt(0).sum()} เดือน",
    f"{worst['kitchen']} ขาดทุนสูงสุด {abs(worst['operating_profit']):,.2f} บาท ควรทบทวนปริมาณขายและค่าใช้จ่ายประจำก่อน",
    f"Mixed Berry ขาดทุนหลังของเสีย {abs(berry['contribution']):,.2f} บาทก่อน overhead และต้นทุนผลไม้เพิ่มขึ้น ขณะที่ราคาขายค่อนข้างคงที่",
    f"{r['promo_check']['profit_before_waste'].lt(0).sum()} จาก {len(r['promo_check'])} คู่เมนู–แพลตฟอร์ม–โปรมีราคาต่ำกว่าต้นทุนผันแปรฐาน ส.ค.",
    f"ฐานพยากรณ์ 3 เดือน {scenario_totals['ฐาน']:,.2f} บาท; แม้ปรับราคาและลดของเสีย 50% ยังขาดทุน {abs(trial_before_saving):,.2f} บาท กำไร {scenario_totals['แผนทดลอง']:,.2f} บาทต้องประหยัด overhead เพิ่มครบ 90,000 บาท"
]
report=Path(__file__).with_name('REPORT.md').read_text(encoding='utf-8')
recommendations=report.split('### Recommendations',1)[1].split('### Tools & methods',1)[0].strip()
report_details='### Tools & methods'+report.split('### Tools & methods',1)[1]
st.title('FruitBlend24 ยอดขายและกำไร')
st.caption('ข้อมูลสังเคราะห์ ก.ย. 2025–ส.ค. 2026 | บาทไทย | แก้ Notebook แล้ว Run All จากนั้นรีเฟรชแอป')
st.caption('ต้นทุนวันเปิดขายบางรายการเป็นค่าประมาณ และ P&L รวมของเสียที่ประมาณเพิ่ม 6 รายการแล้ว')
overview,products,outlook=st.tabs(['ภาพรวม','เมนูและโปรโมชัน','พยากรณ์และวัตถุดิบ'])

with overview:
    a,b,c=st.columns(3)
    a.metric('รายได้ 12 เดือน',f"{r['pnl']['gross_revenue_thb'].sum():,.0f}")
    b.metric('กำไรจากการดำเนินงาน',f"{r['pnl']['operating_profit'].sum():,.0f}")
    c.metric('เดือนที่ขาดทุน',f"{r['pnl']['operating_profit'].lt(0).sum()} / 12")
    st.plotly_chart(px.bar(r['pnl'],x='month',y='operating_profit',title='กำไรจากการดำเนินงานรายเดือน'))
    for text in r['insights']: st.write(text)
    st.subheader('ข้อเสนอแนะ')
    st.markdown(recommendations)
    st.dataframe(r['pnl'][['month','gross_revenue_thb','revenue_gap','gross_profit','gp_gap','contribution','contribution_gap','operating_profit']],hide_index=True)
    st.caption('งบรายเดือน: รายได้ 2.7 ล้านบาท / GP 7 แสนบาท; GP = รายได้ − ผลไม้ − แพ็กเกจ − แรงงานผันแปร; contribution หักคอมมิชชันและของเสีย; operating profit หัก overhead เพิ่ม นิยามงบไม่แจกแจงครบ จึงแสดงส่วนต่างทั้งสองนิยาม')
    st.dataframe(r['kitchens'],hide_index=True)
    with st.expander('Tools, assumptions & further work'):
        st.markdown(report_details)
    with st.expander('คุณภาพข้อมูลและค่าประมาณ'):
        st.dataframe(r['quality'],hide_index=True)
        st.write('Excel ต้นฉบับระบุ exact duplicates และเป็นยอดขายระดับชั่วโมง จึงตัดแถวเหมือนกันเป็นกรณีหลัก พร้อมเทียบกรณีเก็บไว้ทั้งหมด โดยคงของเสียและ overhead เดิม')
        st.dataframe(r['duplicate_sensitivity'],hide_index=True)
        st.dataframe(r['waste_estimates'],hide_index=True)
        st.write(f"ผลไม้วันเปิดขายขาด 75 แถว ใช้ 33.69 บาท/แก้ว; ของเสีย 4 แถว 96 แก้วประมาณต้นทุน 4,002.24 บาท ส่วนบันทึกที่หาย 6 รายการใช้ค่ามัธยฐานของครัว/เมนู/วันในสัปดาห์เดียวกัน ช่วงก่อนและหลัง 4 สัปดาห์ เพิ่มต้นทุน {r['waste_adjustment']:,.2f} บาท รวมใน P&L แล้ว")
        st.caption('จำนวนเสียที่ประมาณอาจเป็นเศษแก้ว ใช้เป็นค่าคาดหมายทางบัญชี ข้อมูลหลังวันที่ขาดใช้เติมประวัติเท่านั้น ควรแทนค่าประมาณด้วยข้อมูลจริงเมื่อได้รับ')

with products:
    st.plotly_chart(px.line(r['monthly_demand'],x='month',y='cups_per_day',color='sku',markers=True,title='ยอดขายเฉลี่ยต่อวัน'))
    st.plotly_chart(px.bar(r['hourly'],x='hour',y='cups_per_day',facet_col='kitchen',facet_col_wrap=2,
        title='ยอดขายเฉลี่ยรายชั่วโมงแยกครัว: 8 สัปดาห์ล่าสุด'))
    st.caption('ใช้ดูช่วงเตรียมของรายครัว การระบุจำนวนพนักงานต้องมีเวลาทำต่อแก้วและกำลังผลิตเพิ่มเติม')
    st.dataframe(r['menu'],hide_index=True)
    sku=st.selectbox('เลือกเมนู',list(r['prices']['sku']),key='sku')
    st.dataframe(r['prices'].loc[r['prices']['sku'].eq(sku),['sku','base_price_thb','avg_price','profit_per_cup','break_even_LM','break_even_Grab']],hide_index=True)
    st.caption('ฐานต้นทุน ส.ค. ราคาคุ้มทุนรวมของเสียเฉลี่ยต่อแก้วแต่ก่อน overhead; Mixed Berry เปิดขาย มี.ค. จึงดูต่อแก้วควบคู่ยอดรวม')
    st.dataframe(r['promo_check'].loc[r['promo_check']['sku'].eq(sku),['platform_name','rate_code_name','selling_price','profit_after_waste','action']],hide_index=True)
    with st.expander('ยอดขายและกำไรโปรที่เกิดขึ้นจริง'):
        st.dataframe(r['promo_history'].loc[r['promo_history']['sku'].eq(sku)],hide_index=True)
    st.caption('แต่ละโปรเกิดคนละช่วงและจำนวนวันต่างกัน จึงใช้กำไรต่อแก้วประกอบการตัดสินใจ ไม่ตีความว่ายอดขายที่ต่างกันเกิดจากโปรอย่างเดียว')

with outlook:
    st.write('Rolling Forecast: เฉลี่ยยอดขาย 28 วันล่าสุด แยกครัวและเมนู แล้วอัปเดตแผนทุก 7 วัน')
    st.caption(f"ข้อมูลจริงถึง {r['forecast_as_of']:%d/%m/%Y} | รอบทบทวนถัดไปตามเคส {r['next_review']:%d/%m/%Y} เติมข้อมูลจริงแล้วรัน Notebook ใหม่ หากไม่มีข้อมูลเพิ่ม ผลจะยังเท่าเดิม")
    a,b=st.columns(2)
    a.metric('WAPE ทยอยอัปเดตทุกสัปดาห์',f"{r['weekly_wape']:.2f}%")
    b.metric('WAPE ตรึงแผน 3 เดือน',f"{r['fixed_wape']:.2f}%")
    st.dataframe(r['weekly_backtest'],hide_index=True)
    st.caption('เทียบช่วงเดียวกันจากวันตัด มี.ค./เม.ย./พ.ค. การอัปเดตใช้ข้อมูลจริงใหม่ทำนายช่วงถัดไป จึงไม่ใช่ความแม่นของการทำนายล่วงหน้า 3 เดือนตั้งแต่วันแรก ช่วงทดสอบซ้อนกันและข้อมูลมีเพียงปีเดียว')
    st.subheader('ผล 3 เดือน แยกเงื่อนไขสะสม')
    st.dataframe(plan_bridge,hide_index=True)
    st.write('ยังยืนยันกำไรไม่ได้: ราคาและของเสียตามแผนยังขาดทุนก่อนประหยัด overhead ก้อน 90,000 บาทต้องมีรายการค่าใช้จ่ายที่ลดได้จริง')
    st.dataframe(r['forecast'],hide_index=True)
    st.caption('แผนทดลอง: ราคา 50/55/55/75/119 บาท; ยอดทั่วไปลด 5%, Berry ลด 20% และงดโปร; อัตราของเสียลดครึ่งหนึ่ง; ตั้งเป้าประหยัดครัวกรุงเทพฯ ครัวละ 15,000 บาท/เดือน สมมติฐานเหล่านี้ยังต้องวัดผลจริง')
    st.plotly_chart(px.bar(r['forecast'],x='month',y='profit_before_savings',color='scenario',barmode='group',
        title='กำไรก่อนเงินประหยัดที่ยังไม่ยืนยัน: ฐานเทียบแผนราคาและของเสีย'))
    st.subheader('Stress test: ยอด Mixed Berry และอัตราของเสีย')
    saving=st.selectbox('สมมติฐานประหยัด overhead ต่อเดือน (บาท)',[0,30000],key='overhead_saving')
    stress=r['scenario_sensitivity'].loc[r['scenario_sensitivity']['monthly_overhead_saving'].eq(saving)]
    matrix=stress.pivot(index='berry_demand_drop_pct',columns='waste_reduction_pct',values='operating_profit_3m')
    matrix.columns=[f'{int(c)}%' for c in matrix.columns]
    st.dataframe(matrix.style.format('{:,.2f}'))
    st.caption('แถว = ยอด Berry ลดลง (%); คอลัมน์ = อัตราของเสียลดลง; ค่า = กำไร 3 เดือน (บาท) ทุกกรณีใช้ราคาทดลองและสมมติยอด 4 เมนูแรกลด 5% ยังไม่ได้วัด elasticity หรือผลต่อการซื้อเมนูอื่น')
    st.subheader('วัตถุดิบตามกรณีฐาน')
    st.caption('ใช้ยอดและอัตราของเสียที่สังเกตล่าสุดจนกว่าจะมีผลทดลองจริง ไม่ใช้เป้าลดของเสีย 50% เป็นฐานสั่งซื้อ')
    st.dataframe(r['inventory'],hide_index=True)
    st.subheader('ตัวอย่างเป้าสต็อกที่ต้องทดสอบก่อนใช้จริง')
    st.dataframe(r['order_plan'],hide_index=True)
    st.caption('หน่วยแก้วเทียบเท่าวัตถุดิบ: ส่ง 1 วัน ทบทวนทุกวัน buffer 0.5 วัน อายุวัตถุดิบสมมติ 3 วัน สต็อกเริ่ม 0 ต้องกรอกของใช้ได้/ของกำลังรับจริงก่อนสั่ง ใช้ FEFO และแบ่งรับ/เตรียมเป็นรอบ การแปลงกิโลกรัมต้องมีสูตรต่อแก้ว')
    st.caption('ทดลอง 14 วันในหนึ่งครัวและสองเมนูโดยคงราคา/โปรเดิม เก็บวันหมดอายุ เหตุที่ทิ้ง และนาทีสินค้าขาด หากขาดสินค้ามากกว่าฐานให้หยุดลดสต็อกและปรับรอบส่งก่อน รายละเอียดอยู่ใน REPORT.md')
