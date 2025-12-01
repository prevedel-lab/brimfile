function c = const(brimfile_module)
    persistent consts
    % the consts were not initialized yet
    if isempty(consts)
        if nargin<1
            error('The function must be initialized before using it')
        end        
        consts = struct();
        consts.StoreType = brimfile_module.StoreType;
        consts.AnalysisResults = brimfile_module.Data.AnalysisResults;
    end
    c = consts;
end