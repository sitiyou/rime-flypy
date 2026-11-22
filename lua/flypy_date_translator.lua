local function translator(input, seg)
  if input == "orq" then
    yield(Candidate("date", seg.start, seg._end, os.date("%Y年%m月%d日"), ""))
    yield(Candidate("date", seg.start, seg._end, os.date("%Y-%m-%d"), " "))
  elseif input == "og" then
    local date = os.date("*t")
    yield(Candidate("date", seg.start, seg._end, os.date("%Y-%m-%d"), ""))
    yield(Candidate("date", seg.start, seg._end, "date +%Y-%m-%d", ""))
    yield(Candidate("date", seg.start, seg._end, date.year .. "年" .. date.month .. "月" .. date.day .. "日", ""))
  end
end

return translator
