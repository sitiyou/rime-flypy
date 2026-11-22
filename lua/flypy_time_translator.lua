local weekdays = { "日", "一", "二", "三", "四", "五", "六" }

local function translator(input, seg)
  if input ~= "ouj" then return end
  local now = os.time()
  local time = os.date("%H:%M", now)
  local cand = Candidate("time", seg.start, seg._end, time, " ")
  cand.quality = 1
  yield(cand)
  local weekday = weekdays[os.date("*t", now).wday]
  yield(Candidate("time", seg.start, seg._end, time .. " 周" .. weekday, ""))
  yield(Candidate("time", seg.start, seg._end, os.date("%H点%M分", now), ""))
end

return translator
