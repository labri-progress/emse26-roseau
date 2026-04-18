package genericsWildcardsClazzMethodParamUpperBoundsMutation;

import java.util.ArrayList;

import testing_lib.genericsWildcardsClazzMethodParamUpperBoundsMutation.GenericsWildcardsClazzMethodParamUpperBoundsMutation;

public class Main extends GenericsWildcardsClazzMethodParamUpperBoundsMutation {

	public static void main(String[] args) {
		GenericsWildcardsClazzMethodParamUpperBoundsMutation constr = new GenericsWildcardsClazzMethodParamUpperBoundsMutation();
		ArrayList<Integer> param1 = new ArrayList<Integer>();
		constr.method1(param1);
	}

	@Override
	public void method1(ArrayList<? extends Integer> param1) {

	}
}
